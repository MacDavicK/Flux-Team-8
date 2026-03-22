import { motion } from "framer-motion";
import { useState } from "react";
import { CalendarPicker } from "~/components/ui/CalendarPicker";

interface StartDatePickerProps {
  onSelect: (dateStr: string) => void;
  disabled?: boolean;
  /** YYYY-MM-DD; pre-selects this date instead of today (suggested by the backend). */
  defaultDate?: string;
  /** YYYY-MM-DD list; forwarded to CalendarPicker as fully-congested disabled cells. */
  disabledDates?: string[];
}

function toISODate(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

function formatDisplay(dateStr: string): string {
  const [y, m, d] = dateStr.split("-").map(Number);
  const date = new Date(y, m - 1, d);
  return date.toLocaleDateString(undefined, {
    weekday: "long",
    month: "long",
    day: "numeric",
  });
}

export function StartDatePicker({
  onSelect,
  disabled,
  defaultDate,
  disabledDates = [],
}: StartDatePickerProps) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const todayStr = toISODate(today);

  // Keep selected in local state just to track the confirm button label
  // CalendarPicker is controlled: we pass value + onChange
  const [selected, setSelected] = useState(defaultDate ?? todayStr);

  function handleConfirm() {
    if (disabled) return;
    onSelect(selected);
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="mt-3 space-y-3"
    >
      <CalendarPicker
        value={selected}
        onChange={setSelected}
        minDate={todayStr}
        showChips
        disabled={disabled}
        disabledDates={disabledDates}
      />

      {/* Selected date label + confirm */}
      <div className="flex items-center justify-between px-1">
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
