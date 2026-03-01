import { format } from "~/utils/date";

export function DateHeader({ date, greeting }: { date?: string; greeting?: string }) {
  const displayDate = date || format(new Date(), "MMMM do");

  return (
    <header className="pt-10 px-6 pb-6 relative z-10 flex justify-between items-end">
      <div>
        {greeting && (
          <p className="text-sm text-charcoal/50 mb-1">{greeting}</p>
        )}
        <h1 className="text-display italic text-4xl text-charcoal leading-tight">
          {displayDate}
        </h1>
      </div>
    </header>
  );
}
