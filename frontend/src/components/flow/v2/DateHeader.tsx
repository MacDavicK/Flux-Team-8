import { Link } from "@tanstack/react-router";
import { User } from "lucide-react";
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

      <Link
        to="/profile"
        className="w-10 h-10 glass-bubble flex items-center justify-center text-river hover:text-sage transition-colors duration-200 active:scale-95 shrink-0 mb-1"
        aria-label="Profile settings"
      >
        <User className="w-[18px] h-[18px]" />
      </Link>
    </header>
  );
}
