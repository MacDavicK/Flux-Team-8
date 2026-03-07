"""
Flux Backend — Goal Planner Agent

A state-machine powered agent that uses an LLM (via OpenRouter) to decompose
high-level goals into weekly milestones and recurring tasks via empathetic
conversation.

States:
  IDLE → GATHERING_TIMELINE → GATHERING_CURRENT_STATE → GATHERING_TARGET
  → GATHERING_PREFERENCES → PLAN_READY → AWAITING_CONFIRMATION → CONFIRMED
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Optional

import httpx
from openai import AsyncOpenAI

from app.config import settings
from app.models.schemas import (
    ConversationState,
    PlanMilestone,
)
from app.services import rag_service

logger = logging.getLogger(__name__)

# ── System Prompt ───────────────────────────────────────────

SYSTEM_PROMPT = """\
You are Flux, an empathetic AI life assistant that helps people turn goals into
actionable daily plans. You are warm, encouraging, and never judgmental.

Your current task is to guide the user through a goal-planning conversation for
a Health & Fitness goal. You must extract the following information one piece at
a time through natural dialogue:

1. **Timeline** — When is their target date / event?
2. **Current State** — e.g. current weight
3. **Target** — e.g. target weight (or suggest a healthy one if asked)
4. **Preferences** — e.g. gym, home workouts, diet, running, etc.

Rules:
- Ask only ONE question at a time.
- Be concise (1–3 sentences max per response).
- Use encouraging emojis sparingly (💪, 🎯, ✨).
- When suggesting a target, be health-conscious and realistic.
- Never be pushy or judgmental about body weight.
- Always be supportive even if the user seems unsure.

Respond with ONLY the next conversational message — no JSON, no markdown headers.
"""

PLAN_GENERATION_PROMPT = """\
You are Flux, an AI life assistant and behavioral scientist. Based on the conversation context below, generate a structured 6-week health & fitness plan.

Context:
- Goal: {goal}
- Timeline: {timeline}
- Current state: {current_state}
- Target: {target}
- Preferences: {preferences}

{expert_context_section}

{rag_section}
Generate a JSON object with this exact structure:
{{
  "plan": [
    {{
      "week": 1,
      "title": "Week 1 milestone title",
      "tasks": ["task 1", "task 2", "task 3"]
    }}
  ],
  "sources": [
    {{
      "title": "Article title",
      "source": "URL"
    }}
  ],
  "sources_used": ["Article title 1", "Article title 2"]
}}

Rules:
- Generate exactly 6 milestones (weeks 1-6).
- Each milestone should have 3-5 concrete, recurring tasks.
- Tasks should be specific and actionable (e.g. "30-min gym session: chest & triceps").
- Progress from lighter to more intense across the weeks.
- Include a mix of the user's preferences (gym, diet, etc.).
- Make it realistic and achievable.
{rag_rules}
- Ground your recommendations in the expert content above when available.
- In "sources_used", list the exact article titles you referenced. If no expert
  content was provided, return an empty array.

Respond with ONLY the JSON object, nothing else.
"""

RAG_RULES = """\
- Ground recommendations in the expert content provided above. Do NOT fabricate advice.
- If the expert content doesn't cover a specific topic, note that in the task description.
- Include a "sources" array listing every article you referenced. Each entry must have "title" and "source" fields.
- Cite sources naturally in task descriptions where applicable (e.g. "Based on CDC guidelines, aim for...").\
"""

NO_RAG_RULES = """\
- If no expert content was provided, generate the best plan from your general knowledge.
- Set "sources" to an empty array [].\
"""

FALLBACK_NO_EXPERT_CONTENT = (
    "I don't have expert guidance for this specific goal yet. "
    "Want me to create a general plan instead?"
)


class GoalPlannerAgent:
    """
    Manages a single goal-planning conversation through a state machine.

    Each conversation gets its own agent instance. The conversation history
    is stored both in-memory (for the LLM context window) and persisted
    to the database via the service layer.
    """

    def __init__(self, conversation_id: str, user_id: str):
        self.conversation_id = conversation_id
        self.user_id = user_id
        self.state = ConversationState.IDLE
        self.context: dict[str, Any] = {}
        self.messages: list[dict[str, str]] = []
        self.plan: Optional[list[PlanMilestone]] = None
        self._sources: list[dict] = []

        self._client = AsyncOpenAI(
            api_key=settings.open_router_api_key,
            base_url=settings.openrouter_base_url,
            http_client=httpx.AsyncClient(trust_env=False),
        )
        self._model = settings.goal_planner_model
        self._rag_available = False

    # ── Public API ──────────────────────────────────────────

    async def process_message(self, user_message: str) -> dict:
        """
        Process a user message and advance the state machine.

        Returns a dict with:
          - message: str (AI response)
          - state: ConversationState
          - suggested_action: Optional[str]
          - plan: Optional[list[PlanMilestone]]
        """
        self.messages.append({"role": "user", "content": user_message})

        result = await self._advance_state(user_message)

        self.messages.append({"role": "assistant", "content": result["message"]})

        return result

    async def start_conversation(self, initial_message: str) -> dict:
        """
        Kick off the conversation. The initial_message is the user's first
        goal statement (e.g. "I want to lose weight for a wedding").
        """
        # Detect if it's a health/fitness goal
        lower = initial_message.lower()
        _FITNESS_KEYWORDS = [
            "lose weight", "weight", "fitness", "gym", "wedding", "health",
            "lose", "loose", "pounds", "shape", "exercise", "workout", "run",
            "running", "diet", "muscle", "strength", "cardio", "fat",
            "tone", "slim", "lean", "fit", "kg", "kilo", "lb", "lbs",
        ]
        if any(kw in lower for kw in _FITNESS_KEYWORDS):
            self.context["goal"] = initial_message
            self.state = ConversationState.GATHERING_TIMELINE
            ai_response = await self._ask_llm(
                f"The user said: \"{initial_message}\". "
                "This is a health & fitness goal. Ask them about their timeline/target date. "
                "Be warm and encouraging."
            )
        else:
            # For MVP, we only support health & fitness
            ai_response = (
                "That's a wonderful goal! 🎯 Right now I'm best at helping with "
                "health & fitness goals. Could you tell me more about a health or "
                "fitness goal you'd like to achieve?"
            )
            self.state = ConversationState.IDLE

        self.messages.append({"role": "user", "content": initial_message})
        self.messages.append({"role": "assistant", "content": ai_response})

        return {
            "message": ai_response,
            "state": self.state,
            "suggested_action": None,
            "plan": None,
        }

    # ── State Machine ───────────────────────────────────────

    async def _advance_state(self, user_message: str) -> dict:
        """Route to the correct handler based on current state."""

        if self.state == ConversationState.IDLE:
            return await self._handle_idle(user_message)
        elif self.state == ConversationState.GATHERING_TIMELINE:
            return await self._handle_timeline(user_message)
        elif self.state == ConversationState.GATHERING_CURRENT_STATE:
            return await self._handle_current_state(user_message)
        elif self.state == ConversationState.GATHERING_TARGET:
            return await self._handle_target(user_message)
        elif self.state == ConversationState.GATHERING_PREFERENCES:
            return await self._handle_preferences(user_message)
        elif self.state == ConversationState.AWAITING_CONFIRMATION:
            return await self._handle_confirmation(user_message)
        else:
            return {
                "message": "This conversation has already been completed. Start a new one to set another goal!",
                "state": self.state,
                "suggested_action": None,
                "plan": None,
            }

    async def _handle_idle(self, message: str) -> dict:
        """User re-engages after an initial non-fitness goal."""
        lower = message.lower()
        _FITNESS_KEYWORDS = [
            "lose weight", "weight", "fitness", "gym", "wedding", "health",
            "lose", "loose", "pounds", "shape", "exercise", "workout", "run",
            "running", "diet", "muscle", "strength", "cardio", "fat",
            "tone", "slim", "lean", "fit", "kg", "kilo", "lb", "lbs",
        ]
        if any(kw in lower for kw in _FITNESS_KEYWORDS):
            self.context["goal"] = message
            self.state = ConversationState.GATHERING_TIMELINE
            ai_response = await self._ask_llm(
                f"The user said: \"{message}\". Ask about their timeline/event date."
            )
        else:
            ai_response = (
                "I'd love to help! For now I specialize in health & fitness goals. "
                "Tell me about a health-related goal and let's build a plan! 💪"
            )
        return {
            "message": ai_response,
            "state": self.state,
            "suggested_action": None,
            "plan": None,
        }

    async def _handle_timeline(self, message: str) -> dict:
        self.context["timeline"] = message
        self.state = ConversationState.GATHERING_CURRENT_STATE

        ai_response = await self._ask_llm(
            f"The user's goal is: \"{self.context['goal']}\". "
            f"Their timeline/event is: \"{message}\". "
            "Now ask about their current state (e.g. current weight). Be gentle and non-judgmental."
        )
        return {
            "message": ai_response,
            "state": self.state,
            "suggested_action": None,
            "plan": None,
        }

    async def _handle_current_state(self, message: str) -> dict:
        self.context["current_state"] = message
        self.state = ConversationState.GATHERING_TARGET

        ai_response = await self._ask_llm(
            f"User's current state: \"{message}\". "
            "Ask what their target is (e.g. target weight), and offer to suggest a healthy goal."
        )
        return {
            "message": ai_response,
            "state": self.state,
            "suggested_action": "Suggest a goal",
            "plan": None,
        }

    async def _handle_target(self, message: str) -> dict:
        lower = message.lower()

        # If the user wants a suggestion, let the LLM suggest one
        if "suggest" in lower:
            ai_response = await self._ask_llm(
                f"The user wants you to suggest a healthy target. "
                f"Their current state: \"{self.context['current_state']}\". "
                f"Timeline: \"{self.context['timeline']}\". "
                "Suggest a realistic, healthy target and then ask about their exercise/diet preferences."
            )
            # Extract a reasonable default
            self.context["target"] = "Healthy target suggested by AI"
        else:
            self.context["target"] = message
            ai_response = await self._ask_llm(
                f"User's target: \"{message}\". "
                "Now ask about their exercise and diet preferences "
                "(gym, home workouts, running, diet changes, etc.)."
            )

        self.state = ConversationState.GATHERING_PREFERENCES
        return {
            "message": ai_response,
            "state": self.state,
            "suggested_action": None,
            "plan": None,
        }

    async def _handle_preferences(self, message: str) -> dict:
        self.context["preferences"] = message
        self.state = ConversationState.AWAITING_CONFIRMATION

        # Generate the plan (with RAG if available)
        plan, sources = await self._generate_plan()
        self.plan = plan
        self._sources = sources

        # Build response message based on whether RAG content was found
        if self._rag_available and self._sources:
            # AC2: Append source citations to the plan summary
            source_lines = "\n".join(
                f'• "{s["title"]}" — {s["source"]}'
                for s in self._sources
            )
            ai_response = (
                "I've put together a personalized 6-week plan based on our conversation "
                "and expert health & fitness research! 🎯\n\n"
                "Here's what I've designed for you. Take a look and let me know if you'd like "
                "to adjust anything, or say **'Looks good!'** to lock it in.\n\n"
                f"📚 Sources:\n{source_lines}"
            )
        else:
            ai_response = (
                f"{FALLBACK_NO_EXPERT_CONTENT}\n\n"
                "I've put together a 6-week plan based on general best practices! 🎯\n\n"
                "Take a look and let me know if you'd like to adjust anything, "
                "or say **'Looks good!'** to lock it in."
            )

        return {
            "message": ai_response,
            "state": self.state,
            "suggested_action": "Looks good!",
            "plan": plan,
            "sources": sources,
        }

    async def _handle_confirmation(self, message: str) -> dict:
        lower = message.lower()
        if any(kw in lower for kw in ["yes", "good", "great", "perfect", "confirm", "lock", "love", "looks good"]):
            self.state = ConversationState.CONFIRMED
            ai_response = (
                "Awesome! Your plan is locked in! 🎉\n\n"
                "I've created your goal, milestones, and recurring tasks. "
                "You'll see them on your calendar. Let's crush this together! 💪"
            )
            return {
                "message": ai_response,
                "state": self.state,
                "suggested_action": None,
                "plan": self.plan,
                "sources": self._sources,
            }
        else:
            # User wants changes — regenerate or adjust
            ai_response = await self._ask_llm(
                f"The user wants to modify the plan. They said: \"{message}\". "
                "Acknowledge their feedback and ask what they'd like to change."
            )
            return {
                "message": ai_response,
                "state": self.state,
                "suggested_action": None,
                "plan": self.plan,
                "sources": self._sources,
            }

    # ── LLM Helpers ─────────────────────────────────────────

    async def _ask_llm(self, instruction: str) -> str:
        """Send the conversation + a specific instruction to GPT-4o-mini."""
        try:
            llm_messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                *self.messages,
                {"role": "user", "content": f"[AGENT INSTRUCTION — not from user]: {instruction}"},
            ]

            response = await self._client.chat.completions.create(
                model=self._model,
                messages=llm_messages,
                temperature=0.7,
                max_tokens=300,
            )
            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            # Fallback responses so the conversation doesn't break
            return self._fallback_response()

    async def _generate_plan(self) -> tuple[list[PlanMilestone], list[dict]]:
        """Ask the LLM to generate a structured 6-week plan, grounded in RAG content.

        Returns ``(milestones, sources)`` where *sources* is a list of
        ``{"title": str, "source": str}`` dicts for every unique article
        that was injected into the prompt.
        """
        sources: list[dict] = []
        formatted = ""

        # --- RAG retrieval (blocking I/O → run in thread) ---------------
        # AC3: If Pinecone is unreachable, fall back silently (AC4).
        _RAG_EXPERT_THRESHOLD = 0.4  # AC3: minimum score to consider results "relevant"
        try:
            query = " ".join(filter(None, [
                self.context.get("goal", ""),
                self.context.get("target", ""),
                self.context.get("preferences", ""),
            ]))
            chunks = await asyncio.to_thread(rag_service.retrieve, query)

            # AC3: If 0 chunks returned OR all scores < 0.4, treat as no-RAG
            has_relevant = any(c["score"] >= _RAG_EXPERT_THRESHOLD for c in chunks)
            if chunks and has_relevant:
                formatted = rag_service.format_rag_context(chunks)

            if formatted:
                # Deduplicate sources by title
                seen_titles: set[str] = set()
                for c in chunks:
                    if c["score"] > settings.rag_relevance_threshold and c["title"] not in seen_titles:
                        seen_titles.add(c["title"])
                        sources.append({"title": c["title"], "source": c["source"]})
                logger.info("RAG: injected %d chars, %d unique sources", len(formatted), len(sources))
            else:
                logger.info("RAG: no chunks above %.2f threshold — generating without expert content", _RAG_EXPERT_THRESHOLD)
        except Exception as e:
            logger.warning("RAG retrieval failed (will generate without): %s", e)

        # --- Plan generation --------------------------------------------
        self._rag_available = bool(sources)
        self._sources = sources

        try:
            if formatted:
                # AC1: inject expert context in the specified format
                expert_context_section = (
                    "EXPERT CONTEXT (use this to ground your plan):\n"
                    "---\n"
                    f"{formatted}\n"
                    "---\n"
                    "You MUST base your plan recommendations on the expert content above.\n"
                    "If the content doesn't cover this goal, say so honestly."
                )
                rag_rules = RAG_RULES
            else:
                expert_context_section = ""
                rag_rules = NO_RAG_RULES

            prompt = PLAN_GENERATION_PROMPT.format(
                goal=self.context.get("goal", ""),
                timeline=self.context.get("timeline", ""),
                current_state=self.context.get("current_state", ""),
                target=self.context.get("target", ""),
                preferences=self.context.get("preferences", ""),
                expert_context_section=expert_context_section,
                rag_rules=rag_rules,
                rag_section="",
            )

            response = await self._client.chat.completions.create(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=2000,
                response_format={"type": "json_object"},
            )

            raw = response.choices[0].message.content.strip()
            data = json.loads(raw)

            milestones = []
            for item in data.get("plan", []):
                milestones.append(
                    PlanMilestone(
                        week=item["week"],
                        title=item["title"],
                        tasks=item["tasks"],
                    )
                )

            # Capture LLM-reported sources (may differ from retrieval sources)
            llm_sources = data.get("sources", [])
            if llm_sources:
                self._sources = llm_sources

            return (milestones, self._sources)

        except Exception as e:
            logger.error("Plan generation failed: %s", e)
            self._rag_available = False
            self._sources = []
            return (self._fallback_plan(), [])

    # ── Fallbacks ───────────────────────────────────────────

    def _fallback_response(self) -> str:
        """Hardcoded fallback if the LLM is unavailable."""
        fallbacks = {
            ConversationState.GATHERING_TIMELINE: "That's a great goal! 💪 When is the event or target date?",
            ConversationState.GATHERING_CURRENT_STATE: "Got it! What do you currently weigh, if you don't mind sharing?",
            ConversationState.GATHERING_TARGET: "And what's your target weight? Or should I suggest a healthy goal?",
            ConversationState.GATHERING_PREFERENCES: "Do you prefer gym, home workouts, or mostly diet changes?",
        }
        return fallbacks.get(self.state, "Tell me more about your goal!")

    def _fallback_plan(self) -> list[PlanMilestone]:
        """Hardcoded fallback plan for the wedding weight loss scenario."""
        return [
            PlanMilestone(week=1, title="Foundation Week", tasks=[
                "30-min walk daily",
                "Track all meals in a food journal",
                "Drink 8 glasses of water daily",
                "Replace sugary drinks with water or herbal tea",
            ]),
            PlanMilestone(week=2, title="Building Momentum", tasks=[
                "3× gym sessions (full body)",
                "Meal prep Sunday for the week",
                "30-min cardio 2× per week",
                "Cut processed snacks",
            ]),
            PlanMilestone(week=3, title="Increasing Intensity", tasks=[
                "4× gym sessions (upper/lower split)",
                "Add 10-min HIIT after strength training",
                "Increase protein intake to 1.6g/kg",
                "Reduce portion sizes by 10%",
            ]),
            PlanMilestone(week=4, title="Consistency Check", tasks=[
                "4× gym sessions",
                "2× cardio sessions (30 min each)",
                "Weekly weigh-in and progress photo",
                "Try one new healthy recipe",
            ]),
            PlanMilestone(week=5, title="Push Phase", tasks=[
                "5× gym sessions",
                "Increase cardio intensity",
                "Fine-tune macros based on progress",
                "Start light core routine daily",
            ]),
            PlanMilestone(week=6, title="Final Sprint & Maintain", tasks=[
                "5× gym sessions with peak intensity",
                "Maintain calorie target",
                "Final weigh-in and measurements",
                "Plan maintenance routine for post-goal",
            ]),
        ]

    # ── Serialization ───────────────────────────────────────

    def to_dict(self) -> dict:
        """Serialize agent state for database persistence."""
        return {
            "conversation_id": self.conversation_id,
            "user_id": self.user_id,
            "state": self.state.value,
            "context": self.context,
            "messages": self.messages,
            "plan": [m.model_dump() for m in self.plan] if self.plan else None,
            "sources": self._sources,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "GoalPlannerAgent":
        """Restore agent state from database."""
        agent = cls(
            conversation_id=data["conversation_id"],
            user_id=data["user_id"],
        )
        agent.state = ConversationState(data["state"])
        agent.context = data.get("context", {})
        agent.messages = data.get("messages", [])
        agent._sources = data.get("sources", [])
        agent._rag_available = bool(agent._sources)

        raw_plan = data.get("plan")
        if raw_plan:
            agent.plan = [PlanMilestone(**m) for m in raw_plan]

        return agent
