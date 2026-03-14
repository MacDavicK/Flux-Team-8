import { Link } from "@tanstack/react-router";
import { ChevronLeft, ChevronRight, User } from "lucide-react";
import { useCallback, useRef } from "react";
import { format } from "~/utils/date";

interface DateHeaderProps {
  date?: string;
  greeting?: string;
  selectedDate?: string | null;
  onDateChange?: (date: string | null) => void;
}

function toLocalDateString(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function todayString(): string {
  return toLocalDateString(new Date());
}

function parseLocalDate(dateStr: string): Date {
  const [y, m, d] = dateStr.split("-").map(Number);
  return new Date(y, m - 1, d);
}

function addDays(dateStr: string, days: number): string {
  const d = parseLocalDate(dateStr);
  d.setDate(d.getDate() + days);
  return toLocalDateString(d);
}

export function DateHeader({
  date: _date,
  greeting,
  selectedDate,
  onDateChange,
}: DateHeaderProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const activeDate = selectedDate ?? todayString();
  const isToday = activeDate === todayString();

  const today = todayString();
  const minDate = addDays(today, -42);
  const maxDate = addDays(today, 42);

  const displayDate = (() => {
    const d = parseLocalDate(activeDate);
    return format(d, "MMMM do");
  })();

  const pendingOffsetRef = useRef(0);

  const go = useCallback(
    (offsetDays: number) => {
      pendingOffsetRef.current += offsetDays;
      if (debounceRef.current) clearTimeout(debounceRef.current);
      debounceRef.current = setTimeout(() => {
        const totalOffset = pendingOffsetRef.current;
        pendingOffsetRef.current = 0;
        const next = addDays(activeDate, totalOffset);
        if (next < minDate || next > maxDate) return;
        const isNextToday = next === today;
        onDateChange?.(isNextToday ? null : next);
      }, 300);
    },
    [activeDate, minDate, maxDate, today, onDateChange],
  );

  const atMin = activeDate <= minDate;
  const atMax = activeDate >= maxDate;

  return (
    <header className="pt-10 px-6 pb-6 relative z-10 flex justify-between items-end">
      <div className="flex-1">
        {greeting && (
          <p className="text-sm text-charcoal/50 mb-1">{greeting}</p>
        )}
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => go(-1)}
            disabled={atMin}
            className="w-7 h-7 flex items-center justify-center rounded-full text-charcoal/50 hover:text-charcoal hover:bg-charcoal/10 active:scale-95 transition-all duration-150 disabled:opacity-30 disabled:pointer-events-none"
            aria-label="Previous day"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>

          <button
            type="button"
            onClick={() => inputRef.current?.showPicker()}
            className="text-display italic text-4xl text-charcoal leading-tight hover:text-river transition-colors duration-150"
            aria-label="Pick a date"
          >
            {displayDate}
          </button>

          <button
            type="button"
            onClick={() => go(1)}
            disabled={atMax}
            className="w-7 h-7 flex items-center justify-center rounded-full text-charcoal/50 hover:text-charcoal hover:bg-charcoal/10 active:scale-95 transition-all duration-150 disabled:opacity-30 disabled:pointer-events-none"
            aria-label="Next day"
          >
            <ChevronRight className="w-4 h-4" />
          </button>

          {/* Hidden native date input for the calendar picker */}
          <input
            ref={inputRef}
            type="date"
            value={activeDate}
            min={minDate}
            max={maxDate}
            onChange={(e) => {
              const val = e.target.value;
              if (!val) return;
              onDateChange?.(val === today ? null : val);
            }}
            className="sr-only"
            aria-hidden="true"
            tabIndex={-1}
          />
        </div>

        {!isToday && (
          <button
            type="button"
            onClick={() => onDateChange?.(null)}
            className="text-xs text-river mt-1 hover:underline"
          >
            Back to today
          </button>
        )}
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
