import { AnimatePresence, motion } from "framer-motion";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useCallback, useRef, useState } from "react";
import { CalendarPicker } from "~/components/ui/CalendarPicker";
import { format } from "~/utils/date";

interface DateHeaderProps {
  date?: string;
  greeting?: string;
  name?: string;
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
  name,
  selectedDate,
  onDateChange,
}: DateHeaderProps) {
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [pickerOpen, setPickerOpen] = useState(false);

  const activeDate = selectedDate ?? todayString();

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

  const displayDayShort = parseLocalDate(activeDate).toLocaleDateString(
    "en-US",
    { weekday: "short" },
  );

  function handlePickerChange(dateStr: string) {
    setPickerOpen(false);
    onDateChange?.(dateStr === today ? null : dateStr);
  }

  return (
    <header
      className="px-5 pb-4 relative z-10"
      style={{ paddingTop: "max(env(safe-area-inset-top, 0px), 44px)" }}
    >
      {/* Row 1: greeting */}
      <div className="flex items-center justify-between mb-3">
        {greeting ? (
          <p className="text-display italic text-sm text-charcoal/40 leading-none">
            {greeting}
            {name && (
              <span className="font-semibold bg-gradient-to-r from-sage to-terracotta bg-clip-text text-transparent text-lg">
                {" "}
                {name}
              </span>
            )}
          </p>
        ) : (
          <span />
        )}
      </div>

      {/* Row 2: ‹ [day, date] › */}
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={() => go(-1)}
          disabled={atMin}
          className="w-8 h-8 flex items-center justify-center rounded-full border border-charcoal/12 text-charcoal/40 hover:text-charcoal hover:border-charcoal/25 active:scale-95 transition-all duration-150 disabled:opacity-20 disabled:pointer-events-none shrink-0"
          aria-label="Previous day"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>

        <button
          type="button"
          onClick={() => setPickerOpen((o) => !o)}
          className="flex items-start gap-1 group"
          aria-label="Pick a date"
          aria-expanded={pickerOpen}
        >
          <span className="text-display italic text-sm text-charcoal/50 leading-none mt-[5px] group-hover:text-river/60 transition-colors duration-150 whitespace-nowrap">
            {displayDayShort},
          </span>
          <span className="text-display italic text-[1.7rem] leading-none text-charcoal group-hover:text-river transition-colors duration-150 whitespace-nowrap">
            {displayDate}
          </span>
        </button>

        <button
          type="button"
          onClick={() => go(1)}
          disabled={atMax}
          className="w-8 h-8 flex items-center justify-center rounded-full border border-charcoal/12 text-charcoal/40 hover:text-charcoal hover:border-charcoal/25 active:scale-95 transition-all duration-150 disabled:opacity-20 disabled:pointer-events-none shrink-0"
          aria-label="Next day"
        >
          <ChevronRight className="w-4 h-4" />
        </button>
      </div>

      {/* Calendar picker popover */}
      <AnimatePresence>
        {pickerOpen && (
          <>
            {/* Backdrop — tap outside to close */}
            <div
              className="fixed inset-0 z-40"
              onClick={() => setPickerOpen(false)}
              aria-hidden="true"
            />
            <motion.div
              initial={{ opacity: 0, y: -8, scale: 0.97 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -8, scale: 0.97 }}
              transition={{ duration: 0.18, ease: "easeOut" }}
              className="absolute left-4 right-4 z-50 mt-2"
            >
              <CalendarPicker
                value={activeDate}
                onChange={handlePickerChange}
                minDate={minDate}
                maxDate={maxDate}
                showChips={false}
                className="shadow-lg"
              />
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </header>
  );
}
