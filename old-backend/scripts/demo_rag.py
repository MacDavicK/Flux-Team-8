#!/usr/bin/env python3
"""
Flux RAG Demo — SCRUM-45/46/47 Progress Update
================================================
A 2-3 minute live terminal demo showing:
  Act 1 — RAG Retrieval (vector store is live, returns relevant chunks)
  Act 2 — Goal Planner + RAG (full conversation → 6-week plan with citations)
  Act 3 — Graceful Fallback (off-domain query → fallback message)

Usage:
    cd backend/
    python scripts/demo_rag.py

Requires: PINECONE_API_KEY, OPEN_ROUTER_API_KEY in .env
"""
from __future__ import annotations

import asyncio
import os
import sys
import time

# ---------------------------------------------------------------------------
# Path setup — allow imports from backend/app/
# ---------------------------------------------------------------------------
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.join(_SCRIPT_DIR, os.pardir)
sys.path.insert(0, os.path.abspath(_BACKEND_DIR))

# ---------------------------------------------------------------------------
# Rich imports (with plain-text fallback)
# ---------------------------------------------------------------------------
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich import box

    console = Console()
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

    class _FallbackConsole:
        def print(self, *args, **kwargs):
            # Strip rich markup for plain output
            text = " ".join(str(a) for a in args)
            print(text)

        def rule(self, title="", **kwargs):
            print(f"\n{'=' * 60}")
            if title:
                print(f"  {title}")
            print(f"{'=' * 60}\n")

    console = _FallbackConsole()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def pause(label: str = "next act"):
    """Gate between acts — presenter controls pacing."""
    console.print()
    input(f"  ⏎  Press Enter for {label}...")
    console.print()


def print_header():
    if HAS_RICH:
        title = Text("Flux — RAG-Powered Goal Planning Demo", style="bold cyan")
        subtitle = Text(
            "SCRUM-45 · SCRUM-46 · SCRUM-47", style="dim"
        )
        console.print(Panel(title, subtitle=subtitle, box=box.DOUBLE, padding=(1, 4)))
    else:
        console.rule("Flux — RAG-Powered Goal Planning Demo")
        console.print("SCRUM-45 · SCRUM-46 · SCRUM-47")
    console.print()
    console.print("[bold]Pipeline:[/bold]  30 expert articles → 355 chunks → Pinecone → Goal Planner" if HAS_RICH else "Pipeline:  30 expert articles → 355 chunks → Pinecone → Goal Planner")
    console.print("[bold]Stack:[/bold]     Pinecone (vectors) · OpenRouter (embeddings + LLM) · FastAPI" if HAS_RICH else "Stack:     Pinecone (vectors) · OpenRouter (embeddings + LLM) · FastAPI")
    console.print()


# ===================================================================
# ACT 1 — RAG Retrieval
# ===================================================================
def act1_retrieval():
    console.rule("[bold green]Act 1 — RAG Retrieval[/bold green]" if HAS_RICH else "Act 1 — RAG Retrieval")
    console.print('Query: [cyan]"lose weight safely beginner exercise"[/cyan]' if HAS_RICH else 'Query: "lose weight safely beginner exercise"')
    console.print()

    from app.services import rag_service

    start = time.time()
    chunks = rag_service.retrieve("lose weight safely beginner exercise", top_k=5)
    elapsed = time.time() - start

    if HAS_RICH:
        table = Table(
            title=f"Top 5 Results ({elapsed:.2f}s)",
            box=box.ROUNDED,
            show_lines=True,
        )
        table.add_column("#", style="dim", width=3)
        table.add_column("Score", style="bold yellow", width=6)
        table.add_column("Article", style="bold", max_width=45)
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
            print(f"  {i}. [{c['score']:.3f}] {c['title']}")
            print(f"     Category: {c.get('category', '—')}")
            print(f"     {preview}")
            print()

    console.print(f"\n[green]✓[/green] {len(chunks)} chunks returned from 355-vector index in {elapsed:.2f}s" if HAS_RICH else f"  ✓ {len(chunks)} chunks returned in {elapsed:.2f}s")


# ===================================================================
# ACT 2 — Goal Planner with RAG
# ===================================================================
async def act2_goal_planner():
    console.rule("[bold green]Act 2 — Goal Planner + RAG Integration[/bold green]" if HAS_RICH else "Act 2 — Goal Planner + RAG Integration")
    console.print("Simulating a full goal-setup conversation…\n")

    from app.agents.goal_planner import GoalPlannerAgent

    agent = GoalPlannerAgent(conversation_id="demo-001", user_id="demo-user")

    # The conversation turns that walk through all 5 states
    turns = [
        ("I want to lose 10 pounds", "IDLE → GATHERING_TIMELINE"),
        ("6 weeks", "GATHERING_TIMELINE → GATHERING_CURRENT_STATE"),
        ("I'm 180 lbs, mostly sedentary, no injuries", "GATHERING_CURRENT_STATE → GATHERING_TARGET"),
        ("170 lbs, I want to feel more energetic", "GATHERING_TARGET → GATHERING_PREFERENCES"),
        ("I prefer morning workouts, mix of cardio and strength, I like running", "GATHERING_PREFERENCES → AWAITING_CONFIRMATION  ← plan generated here"),
    ]

    last_response = None
    for i, (user_msg, transition) in enumerate(turns, 1):
        # Show user message
        if HAS_RICH:
            console.print(f"[bold white]Turn {i}[/bold white] [dim]({transition})[/dim]")
            console.print(f"  [blue]User:[/blue] {user_msg}")
        else:
            print(f"Turn {i} ({transition})")
            print(f"  User: {user_msg}")

        start = time.time()
        response = await agent.process_message(user_msg)
        elapsed = time.time() - start

        ai_msg = response.get("message", "")
        # Truncate long AI responses for readability (except the last one)
        display_msg = ai_msg if i == len(turns) else (ai_msg[:150] + "…" if len(ai_msg) > 150 else ai_msg)

        if HAS_RICH:
            console.print(f"  [green]Flux:[/green] {display_msg}")
            console.print(f"  [dim]({elapsed:.1f}s)[/dim]\n")
        else:
            print(f"  Flux: {display_msg}")
            print(f"  ({elapsed:.1f}s)\n")

        last_response = response

    # --- Show the generated plan ---
    plan = last_response.get("plan", [])
    sources = last_response.get("sources", [])

    if plan:
        if HAS_RICH:
            console.print(Panel("[bold]Generated 6-Week Plan[/bold]", style="cyan"))
            plan_table = Table(box=box.SIMPLE_HEAVY, show_lines=True)
            plan_table.add_column("Week", style="bold", width=6)
            plan_table.add_column("Milestone", style="bold cyan", max_width=30)
            plan_table.add_column("Tasks", max_width=70)

            plan_items = plan if isinstance(plan, list) else []
            for milestone in plan_items:
                # Handle both PlanMilestone objects and dicts
                if hasattr(milestone, "week"):
                    week = str(milestone.week)
                    title = milestone.title
                    tasks = milestone.tasks
                elif isinstance(milestone, dict):
                    week = str(milestone.get("week", "?"))
                    title = milestone.get("title", "—")
                    tasks = milestone.get("tasks", [])
                else:
                    continue

                task_str = "\n".join(f"• {t}" for t in tasks[:4])
                if len(tasks) > 4:
                    task_str += f"\n  (+{len(tasks) - 4} more)"
                plan_table.add_row(week, title, task_str)

            console.print(plan_table)
        else:
            print("  === Generated 6-Week Plan ===")
            for m in plan:
                if hasattr(m, "week"):
                    print(f"  Week {m.week}: {m.title}")
                    for t in m.tasks[:3]:
                        print(f"    • {t}")
                elif isinstance(m, dict):
                    print(f"  Week {m.get('week')}: {m.get('title')}")
                    for t in m.get("tasks", [])[:3]:
                        print(f"    • {t}")

    # --- Show sources ---
    if sources:
        if HAS_RICH:
            console.print(f"\n[bold yellow]📚 Sources ({len(sources)}):[/bold yellow]")
            for s in sources:
                title = s.get("title", "Unknown")
                src = s.get("source", "—")
                console.print(f"  [dim]•[/dim] {title}")
                console.print(f"    [dim]{src}[/dim]")
        else:
            print(f"\n  Sources ({len(sources)}):")
            for s in sources:
                print(f"    • {s.get('title', '?')} — {s.get('source', '?')}")

        console.print(f"\n[green]✓[/green] Plan grounded in expert articles with citations" if HAS_RICH else "\n  ✓ Plan grounded in expert articles with citations")
    else:
        console.print("\n[yellow]⚠ No sources returned (LLM may not have cited them)[/yellow]" if HAS_RICH else "\n  ⚠ No sources returned")


# ===================================================================
# ACT 3 — Graceful Fallback
# ===================================================================
def act3_fallback():
    console.rule("[bold green]Act 3 — Graceful Fallback (Off-Domain)[/bold green]" if HAS_RICH else "Act 3 — Graceful Fallback")
    console.print('Query: [cyan]"learn quantum computing advanced mathematics"[/cyan]\n' if HAS_RICH else 'Query: "learn quantum computing advanced mathematics"\n')

    from app.services import rag_service
    from app.config import settings

    chunks = rag_service.retrieve("learn quantum computing advanced mathematics", top_k=5)

    # Show scores — they should all be low
    relevant = [c for c in chunks if c["score"] > settings.rag_relevance_threshold]
    context = rag_service.format_rag_context(chunks)

    if HAS_RICH:
        if chunks:
            console.print(f"  Top score: [yellow]{chunks[0]['score']:.3f}[/yellow]  (threshold: {settings.rag_relevance_threshold})")
        console.print(f"  Relevant chunks above threshold: [bold]{len(relevant)}[/bold]")
        console.print(f"  Context injected: [bold]{'Yes' if context else 'No — empty string'}[/bold]")
        console.print()

        if not context:
            from app.agents.goal_planner import FALLBACK_NO_EXPERT_CONTENT
            console.print(Panel(
                f"[italic]{FALLBACK_NO_EXPERT_CONTENT}[/italic]",
                title="Fallback Message",
                style="yellow",
                box=box.ROUNDED,
            ))
            console.print("\n[green]✓[/green] Graceful degradation — no hallucinated citations, honest fallback")
        else:
            console.print("[yellow]⚠ Some chunks passed threshold — fallback not triggered[/yellow]")
    else:
        if chunks:
            print(f"  Top score: {chunks[0]['score']:.3f}  (threshold: {settings.rag_relevance_threshold})")
        print(f"  Relevant chunks: {len(relevant)}")
        print(f"  Context injected: {'Yes' if context else 'No'}")
        if not context:
            print("  → Fallback: 'I don't have expert guidance for this specific goal yet.'")
            print("  ✓ Graceful degradation")


# ===================================================================
# Main
# ===================================================================
def main():
    print_header()
    pause("Act 1 — RAG Retrieval")

    act1_retrieval()
    pause("Act 2 — Goal Planner + RAG")

    asyncio.run(act2_goal_planner())
    pause("Act 3 — Fallback")

    act3_fallback()

    console.print()
    console.rule("[bold green]Demo Complete[/bold green]" if HAS_RICH else "Demo Complete")
    if HAS_RICH:
        console.print(Panel(
            "[bold]SCRUM-45[/bold] RAG-Powered Goal Planning — [green]Done[/green]\n"
            "[bold]SCRUM-46[/bold] Article Ingestion & Vector Store — [green]Merged (PR #8, #9)[/green]\n"
            "[bold]SCRUM-47[/bold] RAG → Goal Planner Integration — [green]Merged (PR #10)[/green]",
            title="Ticket Status",
            box=box.ROUNDED,
        ))


if __name__ == "__main__":
    main()