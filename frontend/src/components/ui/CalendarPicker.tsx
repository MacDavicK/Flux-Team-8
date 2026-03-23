/**
 * CalendarPicker — Flux design-system calendar component
 *
 * Design: Organic Minimal Glass
 * Fonts: Fraunces (display month/year) + Satoshi (day cells)
 * Colors: sage / terracotta / stone / charcoal / river (design tokens)
 * Motion: Framer Motion — soft slide on month change, subtle scale on selection
 */

import { AnimatePresence, motion } from "framer-motion";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useState } from "react";
import { cn } from "~/utils/cn";

// ── Helpers ──────────────────────────────────────────────────────────────────

function toISODate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function fromISODate(s: string): Date {
  const [y, m, d] = s.split("-").map(Number);
  return new Date(y, m - 1, d);
}

function addDays(d: Date, n: number): Date {
  const r = new Date(d);
  r.setDate(r.getDate() + n);
  return r;
}

function startOfMonth(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), 1);
}

function isSameDay(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  );
}

const MONTH_NAMES = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

const DAY_LABELS = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"];

// ── Types ─────────────────────────────────────────────────────────────────────

export interface CalendarPickerProps {
  /** ISO date string (YYYY-MM-DD) currently selected */
  value?: string;
  /** Called with ISO date string when user selects a day */
  onChange: (dateStr: string) => void;
  /** Earliest selectable date (ISO string). Defaults to today. */
  minDate?: string;
  /** Latest selectable date (ISO string). No limit by default. */
  maxDate?: string;
  /** Show quick-pick chips (Today, Tomorrow, Next Monday) */
  showChips?: boolean;
  disabled?: boolean;
  className?: string;
  /** YYYY-MM-DD strings for fully-congested days — rendered as disabled with a subtle dot. */
  disabledDates?: string[];
}

// ── Component ─────────────────────────────────────────────────────────────────

export function CalendarPicker({
  value,
  onChange,
  minDate,
  maxDate,
  showChips = true,
  disabled = false,
  className,
  disabledDates = [],
}: CalendarPickerProps) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const min = minDate ? fromISODate(minDate) : today;
  const max = maxDate ? fromISODate(maxDate) : undefined;

  const selected = value ? fromISODate(value) : today;
  const [calMonth, setCalMonth] = useState<Date>(startOfMonth(selected));
  // track slide direction for animation
  const [direction, setDirection] = useState<1 | -1>(1);

  // Quick chips
  const daysUntilMonday = (8 - today.getDay()) % 7 || 7;
  const chips = [
    { label: "Today", date: today },
    { label: "Tomorrow", date: addDays(today, 1) },
    { label: "Next Mon", date: addDays(today, daysUntilMonday) },
  ];

  function select(d: Date) {
    if (disabled) return;
    if (d < min) return;
    if (max && d > max) return;
    onChange(toISODate(d));
  }

  function goMonth(delta: 1 | -1) {
    setDirection(delta);
    setCalMonth((m) => new Date(m.getFullYear(), m.getMonth() + delta, 1));
  }

  // Build 5–6 row grid
  const firstDay = startOfMonth(calMonth);
  const gridStart = addDays(firstDay, -firstDay.getDay());
  const cells: Date[] = Array.from({ length: 42 }, (_, i) =>
    addDays(gridStart, i),
  );
  // trim trailing all-next-month rows
  while (
    cells.length > 35 &&
    cells.slice(-7).every((d) => d.getMonth() !== calMonth.getMonth())
  ) {
    cells.splice(-7, 7);
  }

  const canPrev =
    calMonth.getFullYear() > min.getFullYear() ||
    calMonth.getMonth() > min.getMonth();
  const canNext =
    !max ||
    calMonth.getFullYear() < max.getFullYear() ||
    calMonth.getMonth() < max.getMonth();

  return (
    <div className={cn("space-y-3", className)}>
      {/* Quick chips */}
      {showChips && (
        <div className="flex gap-2">
          {chips.map((chip) => {
            const active = isSameDay(selected, chip.date);
            const past = chip.date < min;
            return (
              <button
                key={chip.label}
                type="button"
                onClick={() => {
                  select(chip.date);
                  setCalMonth(startOfMonth(chip.date));
                }}
                disabled={disabled || past}
                className={cn(
                  "flex-1 py-1.5 rounded-full text-xs font-medium tracking-wide border transition-all duration-150",
                  active
                    ? "bg-sage text-white border-sage shadow-sm"
                    : "bg-white/60 border-charcoal/15 text-charcoal/70 hover:bg-sage/10 hover:border-sage/40 hover:text-sage",
                  "disabled:opacity-30 disabled:cursor-not-allowed",
                )}
              >
                {chip.label}
              </button>
            );
          })}
        </div>
      )}

      {/* Calendar card */}
      <div className="rounded-2xl bg-white/60 backdrop-blur-sm border border-white/70 shadow-sm overflow-hidden">
        {/* Month header */}
        <div className="flex items-center justify-between px-4 pt-3.5 pb-2">
          <button
            type="button"
            onClick={() => goMonth(-1)}
            disabled={!canPrev || disabled}
            className="w-7 h-7 flex items-center justify-center rounded-full hover:bg-black/6 disabled:opacity-20 transition-colors"
            aria-label="Previous month"
          >
            <ChevronLeft className="w-3.5 h-3.5 text-river" />
          </button>

          <AnimatePresence mode="wait" initial={false}>
            <motion.span
              key={`${calMonth.getFullYear()}-${calMonth.getMonth()}`}
              initial={{ opacity: 0, y: direction * -6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: direction * 6 }}
              transition={{ duration: 0.18, ease: "easeOut" }}
              className="text-display italic text-sm font-medium text-charcoal"
            >
              {MONTH_NAMES[calMonth.getMonth()]} {calMonth.getFullYear()}
            </motion.span>
          </AnimatePresence>

          <button
            type="button"
            onClick={() => goMonth(1)}
            disabled={!canNext || disabled}
            className="w-7 h-7 flex items-center justify-center rounded-full hover:bg-black/6 disabled:opacity-20 transition-colors"
            aria-label="Next month"
          >
            <ChevronRight className="w-3.5 h-3.5 text-river" />
          </button>
        </div>

        {/* Day-of-week header row */}
        <div className="grid grid-cols-7 px-3 pb-1">
          {DAY_LABELS.map((d) => (
            <span
              key={d}
              className="text-center text-[10px] font-semibold tracking-wider text-river/50 uppercase"
            >
              {d}
            </span>
          ))}
        </div>

        {/* Date grid */}
        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={`${calMonth.getFullYear()}-${calMonth.getMonth()}`}
            initial={{ opacity: 0, x: direction * 16 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: direction * -16 }}
            transition={{ duration: 0.18, ease: "easeOut" }}
            className="grid grid-cols-7 px-3 pb-3 gap-y-0.5"
          >
            {cells.map((day) => {
              const inMonth = day.getMonth() === calMonth.getMonth();
              const isPast = day < min;
              const isFuture = max ? day > max : false;
              const isCongested = disabledDates.includes(toISODate(day));
              const isDisabled = isPast || isFuture || !inMonth || isCongested;
              const isToday = isSameDay(day, today);
              const isSelected = isSameDay(day, selected);

              return (
                <button
                  key={day.toISOString()}
                  type="button"
                  onClick={() => !isDisabled && select(day)}
                  disabled={isDisabled || disabled}
                  className={cn(
                    "relative h-8 w-full flex items-center justify-center text-[13px] rounded-full transition-all duration-120",
                    // out-of-month: invisible but takes space
                    !inMonth && "invisible pointer-events-none",
                    // past / out-of-range / congested
                    inMonth && isDisabled && "text-river/25 cursor-not-allowed",
                    // normal
                    inMonth &&
                      !isDisabled &&
                      !isSelected &&
                      "text-charcoal hover:bg-sage/12 active:bg-sage/20",
                    // today ring
                    isToday &&
                      !isSelected &&
                      "font-semibold text-sage ring-1 ring-sage/35",
                    // selected — filled sage circle
                    isSelected &&
                      "bg-sage text-white font-semibold shadow-sm scale-105",
                    "disabled:cursor-not-allowed",
                  )}
                >
                  {day.getDate()}
                  {/* Congested indicator — small terracotta dot at the bottom */}
                  {inMonth && isCongested && (
                    <span className="absolute bottom-0.5 left-1/2 -translate-x-1/2 w-1 h-1 rounded-full bg-terracotta/50 pointer-events-none" />
                  )}
                </button>
              );
            })}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}
