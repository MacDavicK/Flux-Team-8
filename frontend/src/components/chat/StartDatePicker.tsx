import { AnimatePresence, motion } from "framer-motion";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useState } from "react";
import { cn } from "~/utils/cn";

interface StartDatePickerProps {
  onSelect: (dateStr: string) => void;
  disabled?: boolean;
}

function formatDisplay(date: Date): string {
  return date.toLocaleDateString(undefined, {
    weekday: "long",
    month: "long",
    day: "numeric",
  });
}

function toISODate(date: Date): string {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, "0");
  const d = String(date.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

function addDays(date: Date, n: number): Date {
  const d = new Date(date);
  d.setDate(d.getDate() + n);
  return d;
}

function startOfMonth(date: Date): Date {
  return new Date(date.getFullYear(), date.getMonth(), 1);
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

export function StartDatePicker({ onSelect, disabled }: StartDatePickerProps) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const [selected, setSelected] = useState<Date>(today);
  const [calendarMonth, setCalendarMonth] = useState<Date>(startOfMonth(today));

  // Determine next Monday
  const daysUntilMonday = (8 - today.getDay()) % 7 || 7;
  const nextMonday = addDays(today, daysUntilMonday);

  const chips = [
    { label: "Today", date: today },
    { label: "Tomorrow", date: addDays(today, 1) },
    { label: "Next Monday", date: nextMonday },
  ];

  function handleChip(date: Date) {
    if (disabled) return;
    setSelected(date);
    setCalendarMonth(startOfMonth(date));
  }

  function handleDayClick(date: Date) {
    if (disabled) return;
    if (date < today) return; // past dates not selectable
    setSelected(date);
  }

  function handleConfirm() {
    if (disabled) return;
    onSelect(toISODate(selected));
  }

  // Build calendar grid
  const firstDay = startOfMonth(calendarMonth);
  const gridStart = addDays(firstDay, -firstDay.getDay()); // always start on Sunday
  const cells: Date[] = [];
  for (let i = 0; i < 42; i++) {
    cells.push(addDays(gridStart, i));
  }
  // Trim trailing rows that are all next month
  while (
    cells.length > 35 &&
    cells.slice(-7).every((d) => d.getMonth() !== calendarMonth.getMonth())
  ) {
    cells.splice(-7, 7);
  }

  function prevMonth() {
    const prev = new Date(
      calendarMonth.getFullYear(),
      calendarMonth.getMonth() - 1,
      1,
    );
    if (prev >= startOfMonth(today)) setCalendarMonth(prev);
  }

  function nextMonth() {
    setCalendarMonth(
      new Date(calendarMonth.getFullYear(), calendarMonth.getMonth() + 1, 1),
    );
  }

  const canGoPrev =
    calendarMonth.getFullYear() > today.getFullYear() ||
    calendarMonth.getMonth() > today.getMonth();

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="mt-3 rounded-2xl bg-white/70 backdrop-blur-sm border border-white/60 shadow-sm p-4 space-y-4"
    >
      {/* Quick chips */}
      <div className="flex gap-2 flex-wrap">
        {chips.map((chip) => (
          <button
            key={chip.label}
            type="button"
            onClick={() => handleChip(chip.date)}
            disabled={disabled}
            className={cn(
              "px-3 py-1.5 rounded-full text-sm font-medium border transition-colors",
              isSameDay(selected, chip.date)
                ? "bg-sage text-white border-sage"
                : "bg-white/80 border-charcoal/20 text-charcoal hover:bg-sage/10 hover:border-sage",
              "disabled:opacity-40 disabled:cursor-not-allowed",
            )}
          >
            {chip.label}
          </button>
        ))}
      </div>

      {/* Calendar */}
      <div className="space-y-2">
        {/* Month nav */}
        <div className="flex items-center justify-between">
          <button
            type="button"
            onClick={prevMonth}
            disabled={!canGoPrev || disabled}
            className="w-7 h-7 flex items-center justify-center rounded-full hover:bg-black/5 disabled:opacity-30 transition-colors"
          >
            <ChevronLeft className="w-4 h-4 text-river" />
          </button>
          <span className="text-sm font-medium text-charcoal">
            {MONTH_NAMES[calendarMonth.getMonth()]}{" "}
            {calendarMonth.getFullYear()}
          </span>
          <button
            type="button"
            onClick={nextMonth}
            disabled={disabled}
            className="w-7 h-7 flex items-center justify-center rounded-full hover:bg-black/5 disabled:opacity-30 transition-colors"
          >
            <ChevronRight className="w-4 h-4 text-river" />
          </button>
        </div>

        {/* Day-of-week headers */}
        <div className="grid grid-cols-7 text-center">
          {DAY_LABELS.map((d) => (
            <span key={d} className="text-xs text-river/60 font-medium pb-1">
              {d}
            </span>
          ))}
        </div>

        {/* Date cells */}
        <AnimatePresence mode="wait">
          <motion.div
            key={`${calendarMonth.getFullYear()}-${calendarMonth.getMonth()}`}
            initial={{ opacity: 0, x: 10 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -10 }}
            transition={{ duration: 0.15 }}
            className="grid grid-cols-7 gap-y-1"
          >
            {cells.map((day) => {
              const isCurrentMonth =
                day.getMonth() === calendarMonth.getMonth();
              const isPast = day < today;
              const isToday = isSameDay(day, today);
              const isSelected = isSameDay(day, selected);

              return (
                <button
                  key={day.toISOString()}
                  type="button"
                  onClick={() => handleDayClick(day)}
                  disabled={isPast || !isCurrentMonth || disabled}
                  className={cn(
                    "h-8 w-full flex items-center justify-center rounded-full text-sm transition-colors",
                    !isCurrentMonth && "opacity-0 pointer-events-none",
                    isPast &&
                      isCurrentMonth &&
                      "text-river/30 cursor-not-allowed",
                    isToday &&
                      !isSelected &&
                      "font-semibold text-sage ring-1 ring-sage/40",
                    isSelected && "bg-sage text-white font-semibold",
                    !isSelected &&
                      !isPast &&
                      isCurrentMonth &&
                      "text-charcoal hover:bg-sage/10",
                    "disabled:cursor-not-allowed",
                  )}
                >
                  {day.getDate()}
                </button>
              );
            })}
          </motion.div>
        </AnimatePresence>
      </div>

      {/* Selected date label + confirm */}
      <div className="flex items-center justify-between pt-1 border-t border-black/5">
        <span className="text-sm text-river">
          Starting{" "}
          <span className="text-charcoal font-medium">
            {formatDisplay(selected)}
          </span>
        </span>
        <motion.button
          type="button"
          onClick={handleConfirm}
          disabled={disabled}
          whileTap={{ scale: 0.97 }}
          className="px-4 py-1.5 rounded-xl bg-sage text-white text-sm font-semibold shadow-sm hover:bg-sage-dark transition-colors disabled:opacity-40"
        >
          Confirm
        </motion.button>
      </div>
    </motion.div>
  );
}
