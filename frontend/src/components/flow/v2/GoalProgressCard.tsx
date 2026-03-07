import { useEffect, useRef, useState } from "react";
import { apiFetch } from "~/lib/apiClient";
import { isClient } from "~/utils/env";

interface GoalProgress {
  goal_id: string;
  title: string;
  completion_pct: number;
  tasks_done: number;
  tasks_total: number;
  on_track: boolean;
  velocity: number;
}

function GoalCard({ goal }: { goal: GoalProgress }) {
  const pct = Math.min(Math.round(goal.completion_pct), 100);
  const radius = 18;
  const circ = 2 * Math.PI * radius;
  const dash = (pct / 100) * circ;

  return (
    <div className="flex items-center gap-3 px-4 py-3 w-full">
      <svg width="44" height="44" className="shrink-0 -rotate-90">
        <circle cx="22" cy="22" r={radius} fill="none" stroke="currentColor" strokeWidth="3" className="text-black/10" />
        <circle
          cx="22"
          cy="22"
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth="3"
          strokeDasharray={`${dash} ${circ}`}
          strokeLinecap="round"
          className={goal.on_track ? "text-sage" : "text-red-400"}
        />
      </svg>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-charcoal truncate">{goal.title}</p>
        <div className="flex items-center gap-2 mt-0.5">
          <p className="text-xs text-charcoal/60">{pct}% complete</p>
          <span className={`text-xs font-medium ${goal.on_track ? "text-sage" : "text-red-400"}`}>
            {goal.on_track ? "· on track" : "· slipping"}
          </span>
        </div>
        <p className="text-xs text-charcoal/40 mt-0.5">
          {goal.tasks_done} / {goal.tasks_total} tasks done
        </p>
      </div>
    </div>
  );
}

export function GoalProgressCard() {
  const [goals, setGoals] = useState<GoalProgress[]>([]);
  const [index, setIndex] = useState(0);

  // Touch swipe state
  const touchStartX = useRef<number | null>(null);

  useEffect(() => {
    if (!isClient()) return;
    apiFetch("/api/v1/goals/progress")
      .then((r) => (r.ok ? r.json() : []))
      .then((data: GoalProgress[]) => {
        if (!Array.isArray(data) || data.length === 0) return;
        setGoals(data);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (goals.length <= 1) return;
    const timer = setInterval(() => {
      setIndex((i) => (i + 1) % goals.length);
    }, 4000);
    return () => clearInterval(timer);
  }, [goals.length]);

  if (goals.length === 0) return null;

  const handleTouchStart = (e: React.TouchEvent) => {
    touchStartX.current = e.touches[0].clientX;
  };

  const handleTouchEnd = (e: React.TouchEvent) => {
    if (touchStartX.current === null) return;
    const diff = touchStartX.current - e.changedTouches[0].clientX;
    if (Math.abs(diff) > 40) {
      if (diff > 0) setIndex((i) => (i + 1) % goals.length);
      else setIndex((i) => (i - 1 + goals.length) % goals.length);
    }
    touchStartX.current = null;
  };

  return (
    <div
      className="mx-4 mb-3 glass-card rounded-2xl overflow-hidden"
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
    >
      <GoalCard goal={goals[index]} />

      {goals.length > 1 && (
        <div className="flex justify-center gap-1.5 pb-2.5">
          {goals.map((_, i) => (
            <button
              key={i}
              onClick={() => setIndex(i)}
              className={`rounded-full transition-all duration-300 ${
                i === index ? "w-4 h-1.5 bg-sage" : "w-1.5 h-1.5 bg-black/15"
              }`}
            />
          ))}
        </div>
      )}
    </div>
  );
}
