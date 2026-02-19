from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import json

from config import settings


class AIAgent:
    """AI Agent for goal analysis and breakdown."""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=0.7,
            openai_api_key=settings.open_router_api_key or "",
            openai_api_base=settings.openrouter_base_url,
        )
    
    async def analyze_goal(self, title: str, description: str, due_date: datetime) -> str:
        """Analyze the goal and provide insights."""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an empathetic AI coach specializing in goal achievement. 
            Analyze the user's goal and provide supportive insights about:
            1. The feasibility and scope of the goal
            2. Key success factors
            3. Potential challenges
            4. Motivational encouragement
            
            Keep your response concise (3-4 sentences) and supportive."""),
            ("user", """Goal: {title}
            Description: {description}
            Due Date: {due_date}
            
            Provide your analysis:""")
        ])
        
        chain = prompt | self.llm
        response = await chain.ainvoke({
            "title": title,
            "description": description or "No description provided",
            "due_date": due_date.strftime("%Y-%m-%d")
        })
        
        return response.content
    
    async def breakdown_goal(
        self, 
        title: str, 
        description: str, 
        due_date: datetime,
        current_date: datetime = None
    ) -> Dict:
        """Break down goal into weekly milestones and daily tasks."""
        if current_date is None:
            current_date = datetime.now()
        
        # Calculate time available
        days_available = (due_date - current_date).days
        weeks_available = max(1, days_available // 7)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an AI planning assistant. Break down the user's goal into:
            1. Weekly milestones (high-level achievements for each week)
            2. Daily tasks (specific, actionable tasks that take 30-60 minutes)
            
            Consider:
            - The goal should be achievable within the timeframe
            - Tasks should be specific and measurable
            - Distribute work evenly across weeks
            - Include review/reflection tasks
            - Make tasks contextually aware and progressive
            
            Return your response as valid JSON with this exact structure:
            {{
                "milestones": [
                    {{
                        "week_number": 1,
                        "title": "Milestone title",
                        "description": "What should be achieved this week"
                    }}
                ],
                "tasks": [
                    {{
                        "milestone_week": 1,
                        "title": "Task title",
                        "description": "Specific action to take",
                        "duration_minutes": 30,
                        "day_offset": 0
                    }}
                ]
            }}
            
            - day_offset is days from start (0 = today, 1 = tomorrow, etc.)
            - Create 3-5 tasks per week
            - Ensure tasks are distributed throughout each week"""),
            ("user", """Goal: {title}
            Description: {description}
            Due Date: {due_date}
            Days Available: {days_available}
            Weeks Available: {weeks_available}
            
            Break down this goal:""")
        ])
        
        chain = prompt | self.llm
        response = await chain.ainvoke({
            "title": title,
            "description": description or "No description provided",
            "due_date": due_date.strftime("%Y-%m-%d"),
            "days_available": days_available,
            "weeks_available": weeks_available
        })
        
        # Parse JSON response
        try:
            breakdown = json.loads(response.content)
            return breakdown
        except json.JSONDecodeError:
            # Fallback to simple breakdown if JSON parsing fails
            return self._create_simple_breakdown(weeks_available)
    
    def _create_simple_breakdown(self, weeks_available: int) -> Dict:
        """Create a simple fallback breakdown."""
        milestones = []
        tasks = []
        
        for week in range(1, weeks_available + 1):
            milestones.append({
                "week_number": week,
                "title": f"Week {week} Milestone",
                "description": f"Progress checkpoint for week {week}"
            })
            
            # Add 3 tasks per week
            for day in range(3):
                day_offset = (week - 1) * 7 + day * 2  # Spread tasks throughout the week
                tasks.append({
                    "milestone_week": week,
                    "title": f"Week {week} - Task {day + 1}",
                    "description": f"Work on goal objectives",
                    "duration_minutes": 30,
                    "day_offset": day_offset
                })
        
        return {"milestones": milestones, "tasks": tasks}
    
    async def suggest_reschedule_time(
        self, 
        task_title: str,
        original_time: datetime,
        available_slots: List[Tuple[datetime, datetime]]
    ) -> datetime:
        """Suggest best time to reschedule a missed task."""
        if not available_slots:
            # Default: reschedule to tomorrow at the same time
            return original_time + timedelta(days=1)
        
        # For now, return the first available slot
        # In a more advanced version, we could use AI to pick the best slot
        return available_slots[0][0]
