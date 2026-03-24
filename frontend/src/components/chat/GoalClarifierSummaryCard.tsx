import type { GoalClarifierAnswer } from "~/types/message";

interface GoalClarifierSummaryCardProps {
  answers: GoalClarifierAnswer[];
}

export function GoalClarifierSummaryCard({
  answers,
}: GoalClarifierSummaryCardProps) {
  return (
    <div className="space-y-3">
      {answers.map((a, i) => (
        <div key={a.question_id}>
          {i > 0 && <div className="border-t border-white/20 mb-3" />}
          <p className="text-[11px] font-medium uppercase tracking-wide opacity-70 leading-tight mb-0.5">
            {a.question}
          </p>
          <p className="text-[15px] leading-snug">{a.answer}</p>
        </div>
      ))}
    </div>
  );
}
