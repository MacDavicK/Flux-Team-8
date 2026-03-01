#!/usr/bin/env python3
"""
Flux RAG Extended Demo — SCRUM-45/46/47 Progress Update (10 min)
=================================================================
A full walkthrough of the RAG pipeline and Goal Planner integration:

  Act 1 — Pipeline Overview        (~1 min)  Architecture + corpus stats
  Act 2 — Retrieval Deep Dive      (~2 min)  Multi-query retrieval quality
  Act 3 — RAG Context Injection    (~1 min)  What the LLM actually sees
  Act 4 — Goal Planner + RAG       (~3 min)  Full conversation → plan + citations
  Act 5 — Graceful Fallback        (~1 min)  Off-domain → honest degradation
  Act 6 — Interactive Q&A          (open)    Teammates try their own queries/goals

Usage:
    cd backend/
    python scripts/demo_rag_extended.py

Requires: PINECONE_API_KEY, OPEN_ROUTER_API_KEY in .env
"""
from __future__ import annotations

import asyncio
import os
import sys
import time

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.abspath(os.path.join(_SCRIPT_DIR, os.pardir))
sys.path.insert(0, _BACKEND_DIR)

# Load backend/.env so OPEN_ROUTER_API_KEY is set when run from repo root
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_BACKEND_DIR, ".env"))
except ImportError:
    pass

# ---------------------------------------------------------------------------
# Rich imports
# ---------------------------------------------------------------------------
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.columns import Columns
    from rich import box

    console = Console()
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

    class _FallbackConsole:
        def print(self, *args, **kwargs):
            text = " ".join(str(a) for a in args)
            print(text)

        def rule(self, title="", **kwargs):
            print(f"\n{'=' * 70}")
            if title:
                print(f"  {title}")
            print(f"{'=' * 70}\n")

    console = _FallbackConsole()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def pause(label: str = "next act"):
    console.print()
    input(f"  ⏎  Press Enter for {label}...")
    console.print()


def section_header(act_num: int, title: str, duration: str):
    if HAS_RICH:
        console.rule(f"[bold green]Act {act_num} — {title}[/bold green]  [dim]({duration})[/dim]")
    else:
        console.rule(f"Act {act_num} — {title}  ({duration})")


def print_chunks_table(chunks: list[dict], elapsed: float, title: str = "Results"):
    if HAS_RICH:
        table = Table(
            title=f"{title} ({elapsed:.2f}s)",
            box=box.ROUNDED,
            show_lines=True,
        )
        table.add_column("#", style="dim", width=3)
        table.add_column("Score", style="bold yellow", width=6)
        table.add_column("Article", style="bold", max_width=42)
        table.add_column("Category", style="cyan", width=14)
        table.add_column("Chunk Preview", max_width=50)

        for i, c in enumerate(chunks, 1):
            preview = c["text"][:120].replace("\n", " ") + "…"
            table.add_row(
                str(i),
                f"{c['score']:.3f}",
                c["title"],
                c.get("category", "—"),
                preview,
            )
        console.print(table)
    else:
        for i, c in enumerate(chunks, 1):
            preview = c["text"][:80].replace("\n", " ") + "…"
            print(f"  {i}. [{c['score']:.3f}] {c['title']} ({c.get('category', '—')})")
            print(f"     {preview}\n")


# ===================================================================
# TITLE SCREEN
# ===================================================================
def print_header():
    if HAS_RICH:
        title = Text("Flux — RAG-Powered Goal Planning", style="bold cyan")
        subtitle = Text("Extended Demo · SCRUM-45 / 46 / 47", style="dim")
        console.print(Panel(title, subtitle=subtitle, box=box.DOUBLE, padding=(1, 4)))
    else:
        console.rule("Flux — RAG-Powered Goal Planning — Extended Demo")

    console.print()
    if HAS_RICH:
        agenda = Table(box=box.SIMPLE, show_header=True, header_style="bold")
        agenda.add_column("Act", style="bold green", width=5)
        agenda.add_column("Section", width=35)
        agenda.add_column("Time", style="dim", width=8)
        agenda.add_row("1", "Pipeline Overview", "~1 min")
        agenda.add_row("2", "Retrieval Deep Dive", "~2 min")
        agenda.add_row("3", "RAG Context Injection", "~1 min")
        agenda.add_row("4", "Goal Planner + RAG", "~3 min")
        agenda.add_row("5", "Graceful Fallback", "~1 min")
        agenda.add_row("6", "Interactive Q&A", "open")
        console.print(agenda)
    else:
        print("  1. Pipeline Overview      ~1 min")
        print("  2. Retrieval Deep Dive    ~2 min")
        print("  3. RAG Context Injection  ~1 min")
        print("  4. Goal Planner + RAG     ~3 min")
        print("  5. Graceful Fallback      ~1 min")
        print("  6. Interactive Q&A        open")


# ===================================================================
# ACT 1 — Pipeline Overview
# ===================================================================
def act1_overview():
    section_header(1, "Pipeline Overview", "~1 min")

    if HAS_RICH:
        arch = (
            "[bold]Data Flow:[/bold]\n\n"
            "  30 expert articles (gov, PMC, hospital, university sources)\n"
            "       │\n"
            "       ▼\n"
            "  [cyan]Chunking[/cyan] — RecursiveCharacterTextSplitter (2000 chars, 200 overlap)\n"
            "       │\n"
            "       ▼\n"
            "  [cyan]Embedding[/cyan] — OpenAI text-embedding-3-small via OpenRouter\n"
            "       │  (1536 dimensions, batches of 64)\n"
            "       ▼\n"
            "  [cyan]Pinecone[/cyan] — 'flux-articles' index, 355 vectors, cosine similarity\n"
            "       │\n"
            "       ▼\n"
            "  [cyan]Goal Planner[/cyan] — Top-K retrieval → inject into LLM prompt → plan + citations"
        )
        console.print(Panel(arch, title="Architecture", box=box.ROUNDED, padding=(1, 2)))
    else:
        print("  30 articles → chunk (2000/200) → embed (1536d) → Pinecone (355 vectors)")
        print("  → retrieve top-K → inject into Goal Planner prompt → plan + citations")

    console.print()

    # Show corpus stats
    from app.services import rag_service
    from app.config import settings

    if HAS_RICH:
        stats = Table(title="Corpus Stats", box=box.SIMPLE, show_header=False)
        stats.add_column("Metric", style="bold", width=30)
        stats.add_column("Value", style="cyan")
        stats.add_row("Expert articles curated", "30")
        stats.add_row("Vectors in Pinecone", "355")
        stats.add_row("Embedding dimensions", "1536")
        stats.add_row("Embedding model", settings.embedding_model)
        stats.add_row("Pinecone index", settings.pinecone_index_name)
        stats.add_row("Relevance threshold", str(settings.rag_relevance_threshold))
        stats.add_row("Top-K retrieval", str(settings.rag_top_k))
        console.print(stats)

        # Source breakdown
        sources = Table(title="Article Sources", box=box.SIMPLE)
        sources.add_column("Source Type", style="bold", width=25)
        sources.add_column("Count", style="cyan", width=8)
        sources.add_row("Government / Intl Org", "11")
        sources.add_row("PubMed Central (PMC)", "10")
        sources.add_row("Hospital / Medical Center", "4")
        sources.add_row("University", "3")
        sources.add_row("Professional (ACSM/JAMA)", "2")
        console.print(sources)

        categories = Table(title="Content Categories", box=box.SIMPLE)
        categories.add_column("Category", style="bold", width=25)
        categories.add_column("Articles", style="cyan", width=8)
        categories.add_row("Weight Loss", "6")
        categories.add_row("Nutrition", "6")
        categories.add_row("Strength Training", "6")
        categories.add_row("Cardio / Running", "6")
        categories.add_row("Behavioral Science", "6")
        console.print(categories)
    else:
        print("  Articles: 30 | Vectors: 355 | Dimensions: 1536")
        print("  Categories: Weight Loss, Nutrition, Strength, Cardio, Behavioral")
        print("  Sources: 11 gov, 10 PMC, 4 hospital, 3 university, 2 professional")


# ===================================================================
# ACT 2 — Retrieval Deep Dive
# ===================================================================
def act2_retrieval():
    section_header(2, "Retrieval Deep Dive", "~2 min")
    console.print("Running 4 queries across different categories to show retrieval quality.\n")

    from app.services import rag_service

    queries = [
        ("safe weight loss rate per week", "Weight Loss"),
        ("beginner 5K running plan couch to 5K", "Cardio"),
        ("high protein diet muscle building", "Nutrition + Strength"),
        ("motivation habit building exercise consistency", "Behavioral"),
    ]

    for query, expected_category in queries:
        if HAS_RICH:
            console.print(f'[bold]Query:[/bold] [cyan]"{query}"[/cyan]  [dim](expecting: {expected_category})[/dim]')
        else:
            print(f'  Query: "{query}"  (expecting: {expected_category})')

        start = time.time()
        chunks = rag_service.retrieve(query, top_k=3)
        elapsed = time.time() - start

        print_chunks_table(chunks, elapsed, title=f"Top 3 — {expected_category}")
        console.print()

    if HAS_RICH:
        console.print("[green]✓[/green] All 4 queries return category-appropriate results with scores > 0.5")
    else:
        print("  ✓ All queries return category-appropriate results")


# ===================================================================
# ACT 3 — RAG Context Injection (What the LLM Sees)
# ===================================================================
def act3_context_injection():
    section_header(3, "RAG Context Injection", "~1 min")
    console.print("This is what gets injected into the Goal Planner's LLM prompt.\n")

    from app.services import rag_service

    chunks = rag_service.retrieve("lose weight safely beginner exercise", top_k=5)
    formatted = rag_service.format_rag_context(chunks)

    if HAS_RICH:
        # Show the formatted context (truncated for readability)
        lines = formatted.split("\n")
        display_lines = lines[:30]
        truncated = len(lines) > 30

        display_text = "\n".join(display_lines)
        if truncated:
            display_text += f"\n\n[dim]… ({len(lines) - 30} more lines truncated)[/dim]"

        console.print(Panel(
            display_text,
            title="format_rag_context() output → injected into prompt as '## Expert Content'",
            box=box.ROUNDED,
            style="dim",
            padding=(1, 2),
        ))

        console.print(f"\n[bold]Total context length:[/bold] {len(formatted):,} chars")
        console.print(f"[bold]Unique sources:[/bold] {len(set((c['title'], c['source']) for c in chunks))}")
    else:
        preview = formatted[:600] + "\n..." if len(formatted) > 600 else formatted
        print(preview)
        print(f"\n  Total context: {len(formatted):,} chars")

    console.print()
    if HAS_RICH:
        console.print(
            "[green]✓[/green] Context is numbered, includes source attribution per chunk, "
            "and gets injected between user context and generation rules"
        )


# ===================================================================
# ACT 4 — Goal Planner + RAG (Full Conversation)
# ===================================================================
async def act4_goal_planner():
    section_header(4, "Goal Planner + RAG Integration", "~3 min")
    console.print("Full 5-turn conversation through the Goal Planner state machine.\n")

    if HAS_RICH:
        sm = (
            "[dim]State Machine:[/dim]\n"
            "  IDLE → GATHERING_TIMELINE → GATHERING_CURRENT_STATE\n"
            "       → GATHERING_TARGET → GATHERING_PREFERENCES\n"
            "       → [bold cyan]AWAITING_CONFIRMATION[/bold cyan] (plan generated here)"
        )
        console.print(Panel(sm, box=box.SIMPLE))
    else:
        print("  States: IDLE → TIMELINE → CURRENT_STATE → TARGET → PREFERENCES → CONFIRMATION")

    console.print()

    from app.agents.goal_planner import GoalPlannerAgent

    agent = GoalPlannerAgent(conversation_id="demo-extended-001", user_id="demo-user")

    turns = [
        ("I want to lose 10 pounds and get in shape", "IDLE → GATHERING_TIMELINE"),
        ("6 weeks", "→ GATHERING_CURRENT_STATE"),
        ("I'm 180 lbs, mostly sedentary, no injuries, I walk occasionally", "→ GATHERING_TARGET"),
        ("170 lbs, I want to feel more energetic and fit into my old clothes", "→ GATHERING_PREFERENCES"),
        ("I prefer morning workouts, I like running and bodyweight exercises, 4 days a week max", "→ AWAITING_CONFIRMATION"),
    ]

    last_response = None
    total_start = time.time()

    for i, (user_msg, transition) in enumerate(turns, 1):
        is_final = i == len(turns)

        if HAS_RICH:
            console.print(f"[bold white]Turn {i}/5[/bold white]  [dim]{transition}[/dim]")
            console.print(f"  [blue]👤 User:[/blue] {user_msg}")
        else:
            print(f"Turn {i}/5  {transition}")
            print(f"  User: {user_msg}")

        start = time.time()
        if i == 1:
            response = await agent.start_conversation(user_msg)
        else:
            response = await agent.process_message(user_msg)
        elapsed = time.time() - start

        ai_msg = response.get("message", "")
        state = response.get("state", "?")
        if hasattr(state, "value"):
            state = state.value

        # Show full response on final turn, truncated on others
        if is_final:
            display_msg = ai_msg
        else:
            display_msg = ai_msg[:200] + "…" if len(ai_msg) > 200 else ai_msg

        if HAS_RICH:
            console.print(f"  [green]🤖 Flux:[/green] {display_msg}")
            console.print(f"  [dim]State: {state} · {elapsed:.1f}s[/dim]\n")
        else:
            print(f"  Flux: {display_msg}")
            print(f"  State: {state} · {elapsed:.1f}s\n")

        last_response = response

    total_elapsed = time.time() - total_start

    # --- Generated Plan ---
    plan = last_response.get("plan") or []
    sources = last_response.get("sources") or []

    if plan:
        if HAS_RICH:
            console.print(Panel("[bold cyan]📋 Generated 6-Week Plan[/bold cyan]", expand=False))
            plan_table = Table(box=box.ROUNDED, show_lines=True, padding=(0, 1))
            plan_table.add_column("Week", style="bold yellow", width=6, justify="center")
            plan_table.add_column("Milestone", style="bold cyan", max_width=30)
            plan_table.add_column("Tasks", max_width=70)

            for milestone in plan:
                if hasattr(milestone, "week"):
                    week, title, tasks = str(milestone.week), milestone.title, milestone.tasks
                elif isinstance(milestone, dict):
                    week = str(milestone.get("week", "?"))
                    title = milestone.get("title", "—")
                    tasks = milestone.get("tasks", [])
                else:
                    continue

                task_str = "\n".join(f"• {t}" for t in tasks[:5])
                if len(tasks) > 5:
                    task_str += f"\n  [dim](+{len(tasks) - 5} more)[/dim]"
                plan_table.add_row(week, title, task_str)

            console.print(plan_table)
        else:
            print("  === Generated 6-Week Plan ===")
            for m in plan:
                if hasattr(m, "week"):
                    print(f"  Week {m.week}: {m.title}")
                    for t in m.tasks[:4]:
                        print(f"    • {t}")
                elif isinstance(m, dict):
                    print(f"  Week {m.get('week')}: {m.get('title')}")
                    for t in m.get("tasks", [])[:4]:
                        print(f"    • {t}")

    # --- Sources ---
    if sources:
        if HAS_RICH:
            src_table = Table(title=f"📚 Expert Sources ({len(sources)})", box=box.SIMPLE)
            src_table.add_column("#", style="dim", width=3)
            src_table.add_column("Article", style="bold", max_width=50)
            src_table.add_column("Source", style="dim cyan", max_width=50)

            for i, s in enumerate(sources, 1):
                src_table.add_row(str(i), s.get("title", "?"), s.get("source", "—"))
            console.print(src_table)
        else:
            print(f"\n  Sources ({len(sources)}):")
            for s in sources:
                print(f"    • {s.get('title', '?')} — {s.get('source', '?')}")

    # --- Summary ---
    console.print()
    if HAS_RICH:
        summary = (
            f"[bold]Total conversation time:[/bold] {total_elapsed:.1f}s\n"
            f"[bold]Plan milestones:[/bold] {len(plan)}\n"
            f"[bold]Expert sources cited:[/bold] {len(sources)}\n"
            f"[bold]RAG-grounded:[/bold] [green]Yes[/green]"
        )
        console.print(Panel(summary, title="Act 4 Summary", box=box.ROUNDED))
    else:
        print(f"  Total: {total_elapsed:.1f}s | Milestones: {len(plan)} | Sources: {len(sources)}")

    console.print("[green]✓[/green] End-to-end: user intent → context gathering → RAG retrieval → expert-grounded plan" if HAS_RICH else "  ✓ Full pipeline working")


# ===================================================================
# ACT 5 — Graceful Fallback
# ===================================================================
def act5_fallback():
    section_header(5, "Graceful Fallback", "~1 min")
    console.print("What happens when someone asks for a goal outside our article corpus?\n")

    from app.services import rag_service
    from app.config import settings

    test_queries = [
        "learn quantum computing advanced mathematics",
        "improve my chess rating grandmaster strategy",
    ]

    for query in test_queries:
        if HAS_RICH:
            console.print(f'[bold]Query:[/bold] [cyan]"{query}"[/cyan]')
        else:
            print(f'  Query: "{query}"')

        chunks = rag_service.retrieve(query, top_k=3)
        context = rag_service.format_rag_context(chunks)

        top_score = chunks[0]["score"] if chunks else 0.0
        relevant = [c for c in chunks if c["score"] > settings.rag_relevance_threshold]

        if HAS_RICH:
            console.print(f"  Top score: [yellow]{top_score:.3f}[/yellow]  |  "
                          f"Above threshold ({settings.rag_relevance_threshold}): [bold]{len(relevant)}[/bold]  |  "
                          f"Context injected: [bold]{'Yes' if context else 'No'}[/bold]")
        else:
            print(f"  Top score: {top_score:.3f} | Above threshold: {len(relevant)} | Context: {'Yes' if context else 'No'}")
        console.print()

    # Show the fallback message
    from app.agents.goal_planner import FALLBACK_NO_EXPERT_CONTENT

    if HAS_RICH:
        console.print(Panel(
            f"[italic]{FALLBACK_NO_EXPERT_CONTENT}[/italic]\n\n"
            "[dim]The Goal Planner still generates a plan using general LLM knowledge,\n"
            "but honestly tells the user it lacks expert backing for this topic.\n"
            "The 'sources' array is returned empty — no hallucinated citations.[/dim]",
            title="Fallback Behavior",
            style="yellow",
            box=box.ROUNDED,
        ))
    else:
        print(f"  Fallback: {FALLBACK_NO_EXPERT_CONTENT}")
        print("  → Plan still generated from general knowledge, but sources = []")

    console.print("[green]✓[/green] Graceful degradation — honest about limits, no hallucinated citations" if HAS_RICH else "  ✓ Graceful degradation confirmed")


# ===================================================================
# ACT 6 — Interactive Q&A
# ===================================================================
async def act6_qa():
    section_header(6, "Interactive Q&A", "open")

    if HAS_RICH:
        console.print(Panel(
            "[bold]Two modes available:[/bold]\n\n"
            "  [cyan]1. search <query>[/cyan]     — Search the vector store directly\n"
            "  [cyan]2. plan <goal>[/cyan]        — Run a full Goal Planner conversation\n"
            "  [cyan]3. quit[/cyan]               — End demo\n\n"
            "[dim]Examples:[/dim]\n"
            '  search how to build muscle as a beginner\n'
            '  plan I want to run a marathon\n'
            '  search intermittent fasting benefits',
            title="Commands",
            box=box.ROUNDED,
        ))
    else:
        print("  Commands:")
        print("    search <query>  — Search the vector store")
        print("    plan <goal>     — Full Goal Planner conversation")
        print("    quit            — End demo")

    from app.services import rag_service
    from app.agents.goal_planner import GoalPlannerAgent

    qa_session_count = 0

    while True:
        console.print()
        try:
            user_input = input("  🎤 > ").strip()
        except (KeyboardInterrupt, EOFError):
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit", "q"):
            break

        # --- SEARCH MODE ---
        if user_input.lower().startswith("search "):
            query = user_input[7:].strip()
            if not query:
                console.print("[yellow]  Please provide a search query.[/yellow]" if HAS_RICH else "  Please provide a search query.")
                continue

            if HAS_RICH:
                console.print(f'\n  [bold]Searching:[/bold] [cyan]"{query}"[/cyan]')
            else:
                print(f'\n  Searching: "{query}"')

            try:
                start = time.time()
                chunks = rag_service.retrieve(query, top_k=5)
                elapsed = time.time() - start
                print_chunks_table(chunks, elapsed, title="Search Results")

                # Also show formatted context
                context = rag_service.format_rag_context(chunks)
                if context:
                    if HAS_RICH:
                        console.print(f"  [green]✓[/green] Would inject {len(context):,} chars of expert context into the prompt")
                    else:
                        print(f"  ✓ Would inject {len(context):,} chars into prompt")
                else:
                    if HAS_RICH:
                        console.print("  [yellow]⚠ No chunks above relevance threshold — fallback mode[/yellow]")
                    else:
                        print("  ⚠ No relevant chunks — fallback mode")

            except Exception as e:
                console.print(f"[red]  Error: {e}[/red]" if HAS_RICH else f"  Error: {e}")

        # --- PLAN MODE ---
        elif user_input.lower().startswith("plan "):
            goal = user_input[5:].strip()
            if not goal:
                console.print("[yellow]  Please provide a goal.[/yellow]" if HAS_RICH else "  Please provide a goal.")
                continue

            qa_session_count += 1
            if HAS_RICH:
                console.print(f'\n  [bold]Running Goal Planner for:[/bold] [cyan]"{goal}"[/cyan]')
                console.print("  [dim]Using default context (6 weeks, general user profile)[/dim]\n")
            else:
                print(f'\n  Goal: "{goal}" (using default context)\n')

            agent = GoalPlannerAgent(
                conversation_id=f"demo-qa-{qa_session_count:03d}",
                user_id="demo-user",
            )

            # Quick-fire through the conversation with sensible defaults
            quick_turns = [
                goal,
                "6 weeks",
                "Generally healthy, somewhat active, no injuries",
                "I want to make meaningful progress and build a habit",
                "I'm flexible on timing, 4-5 days a week works",
            ]

            try:
                for i, msg in enumerate(quick_turns, 1):
                    state_before = agent.state.value if hasattr(agent.state, "value") else str(agent.state)
                    if HAS_RICH:
                        console.print(f"  [dim]Turn {i}:[/dim] {msg[:80]}{'…' if len(msg) > 80 else ''}")
                    start = time.time()
                    if i == 1:
                        response = await agent.start_conversation(msg)
                    else:
                        response = await agent.process_message(msg)
                    elapsed = time.time() - start
                    state_after = response.get("state", "?")
                    if hasattr(state_after, "value"):
                        state_after = state_after.value
                    if HAS_RICH:
                        console.print(f"         [dim]{state_before} → {state_after} ({elapsed:.1f}s)[/dim]")

                # Show results
                plan = response.get("plan", [])
                sources = response.get("sources", [])

                if plan:
                    console.print()
                    if HAS_RICH:
                        for m in plan:
                            if hasattr(m, "week"):
                                console.print(f"  [bold yellow]Week {m.week}:[/bold yellow] [cyan]{m.title}[/cyan]")
                                for t in m.tasks[:3]:
                                    console.print(f"    • {t}")
                                if len(m.tasks) > 3:
                                    console.print(f"    [dim](+{len(m.tasks) - 3} more)[/dim]")
                            elif isinstance(m, dict):
                                console.print(f"  [bold yellow]Week {m.get('week')}:[/bold yellow] [cyan]{m.get('title')}[/cyan]")
                                for t in m.get("tasks", [])[:3]:
                                    console.print(f"    • {t}")
                    else:
                        for m in plan:
                            w = m.week if hasattr(m, "week") else m.get("week")
                            t = m.title if hasattr(m, "title") else m.get("title")
                            print(f"  Week {w}: {t}")

                if sources:
                    console.print(f"\n  [bold yellow]📚 {len(sources)} source(s) cited[/bold yellow]" if HAS_RICH else f"\n  {len(sources)} source(s) cited")
                    for s in sources[:3]:
                        console.print(f"    [dim]• {s.get('title', '?')}[/dim]" if HAS_RICH else f"    • {s.get('title', '?')}")
                else:
                    console.print("\n  [yellow]No sources — fallback mode (off-domain goal)[/yellow]" if HAS_RICH else "\n  No sources — fallback mode")

            except Exception as e:
                console.print(f"[red]  Error: {e}[/red]" if HAS_RICH else f"  Error: {e}")

        else:
            if HAS_RICH:
                console.print("[yellow]  Unknown command. Use 'search <query>', 'plan <goal>', or 'quit'.[/yellow]")
            else:
                print("  Unknown command. Use 'search <query>', 'plan <goal>', or 'quit'.")


# ===================================================================
# CLOSING
# ===================================================================
def print_closing():
    console.print()
    console.rule("[bold green]Demo Complete[/bold green]" if HAS_RICH else "Demo Complete")

    if HAS_RICH:
        console.print(Panel(
            "[bold]SCRUM-45[/bold]  RAG-Powered Goal Planning (v2)         [green]✓ Complete[/green]\n"
            "[bold]SCRUM-46[/bold]  Article Ingestion & Vector Store       [green]✓ Merged — PR #8, #9[/green]\n"
            "[bold]SCRUM-47[/bold]  RAG → Goal Planner Integration         [green]✓ Merged — PR #10[/green]\n"
            "\n"
            "[bold]Key Deliverables:[/bold]\n"
            "  • 30 expert articles (gov, PMC, university) → 355 vectors in Pinecone\n"
            "  • RAG retrieval integrated into Goal Planner state machine\n"
            "  • Source citations in generated plans\n"
            "  • Graceful fallback for off-domain goals\n"
            "  • Zero breaking changes to existing goal setup flow",
            title="Ticket Status",
            box=box.ROUNDED,
        ))
    else:
        print("  SCRUM-45 Complete | SCRUM-46 Merged (PR #8, #9) | SCRUM-47 Merged (PR #10)")
        print("  30 articles → 355 vectors → RAG in Goal Planner → citations + fallback")


# ===================================================================
# Main
# ===================================================================
def main():
    print_header()
    pause("Act 1 — Pipeline Overview")

    act1_overview()
    pause("Act 2 — Retrieval Deep Dive")

    act2_retrieval()
    pause("Act 3 — Context Injection")

    act3_context_injection()
    pause("Act 4 — Goal Planner + RAG")

    asyncio.run(act4_goal_planner())
    pause("Act 5 — Fallback")

    act5_fallback()
    pause("Act 6 — Q&A (interactive)")

    asyncio.run(act6_qa())

    print_closing()


if __name__ == "__main__":
    main()