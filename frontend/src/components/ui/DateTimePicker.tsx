/**
 * DateTimePicker — Calendar + time wheel replacement for <input type="datetime-local">
 *
 * Two-step UI:
 *  1. CalendarPicker to select the date
 *  2. Scrollable hour / minute / AM-PM picker (iOS-style but flat)
 *
 * Returns a UTC ISO string via `onChange`.
 */

import { AnimatePresence, motion } from "framer-motion";
import { Clock } from "lucide-react";
import { useState } from "react";
import { cn } from "~/utils/cn";
import { CalendarPicker } from "./CalendarPicker";

// ── Helpers ───────────────────────────────────────────────────────────────────

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

function formatTimeDisplay(hour24: number, minute: number): string {
  const period = hour24 >= 12 ? "PM" : "AM";
  const h = hour24 % 12 || 12;
  return `${h}:${String(minute).padStart(2, "0")} ${period}`;
}

function formatDateDisplay(dateStr: string): string {
  const d = fromISODate(dateStr);
  return d.toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

const HOURS_12 = Array.from({ length: 12 }, (_, i) => i + 1); // 1–12
const MINUTES = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55];

// ── Types ─────────────────────────────────────────────────────────────────────

export interface DateTimePickerProps {
  /** UTC ISO string */
  value?: string;
  onChange: (utcIso: string) => void;
  /** Earliest selectable (ISO date string YYYY-MM-DD). Defaults to today. */
  minDate?: string;
  disabled?: boolean;
  className?: string;
}

type Step = "date" | "time";

// ── Component ─────────────────────────────────────────────────────────────────

export function DateTimePicker({
  value,
  onChange,
  minDate,
  disabled = false,
  className,
}: DateTimePickerProps) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  // Parse current value or default
  const initial = value
    ? new Date(value)
    : (() => {
        const d = new Date();
        d.setMinutes(
          d.getMinutes() < 55 ? Math.ceil(d.getMinutes() / 5) * 5 : 0,
          0,
          0,
        );
        if (d.getMinutes() === 0) d.setHours(d.getHours() + 1);
        return d;
      })();

  const [step, setStep] = useState<Step>("date");
  const [dateStr, setDateStr] = useState<string>(toISODate(initial));

  // Time state in 12h format
  const initHour12 = initial.getHours() % 12 || 12;
  const initMinute = (Math.round(initial.getMinutes() / 5) * 5) % 60;
  const initPeriod: "AM" | "PM" = initial.getHours() >= 12 ? "PM" : "AM";

  const [hour12, setHour12] = useState<number>(initHour12);
  const [minute, setMinute] = useState<number>(initMinute);
  const [period, setPeriod] = useState<"AM" | "PM">(initPeriod);

  function buildAndEmit(ds: string, h: number, min: number, p: "AM" | "PM") {
    const [y, mo, d] = ds.split("-").map(Number);
    let hour24 = h % 12;
    if (p === "PM") hour24 += 12;
    const dt = new Date(y, mo - 1, d, hour24, min, 0, 0);
    onChange(dt.toISOString());
  }

  function handleDateConfirm(ds: string) {
    setDateStr(ds);
    setStep("time");
  }

  function handleTimeConfirm() {
    buildAndEmit(dateStr, hour12, minute, period);
  }

  const hour24Display = (hour12 % 12) + (period === "PM" ? 12 : 0);
  const timeDisplay = formatTimeDisplay(hour24Display, minute);
  const minDateStr = minDate ?? toISODate(today);

  return (
    <div className={cn("space-y-3", className)}>
      {/* Step tabs */}
      <div className="flex gap-1 p-1 rounded-xl bg-black/5">
        {(["date", "time"] as Step[]).map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => setStep(s)}
            disabled={disabled}
            className={cn(
              "flex-1 py-1.5 rounded-lg text-xs font-semibold tracking-wide transition-all duration-150 capitalize",
              step === s
                ? "bg-white shadow-sm text-charcoal"
                : "text-river hover:text-charcoal",
            )}
          >
            {s === "date"
              ? `📅 ${formatDateDisplay(dateStr)}`
              : `🕐 ${timeDisplay}`}
          </button>
        ))}
      </div>

      {/* Step content */}
      <AnimatePresence mode="wait" initial={false}>
        {step === "date" ? (
          <motion.div
            key="date"
            initial={{ opacity: 0, x: -12 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -12 }}
            transition={{ duration: 0.18 }}
          >
            <CalendarPicker
              value={dateStr}
              onChange={handleDateConfirm}
              minDate={minDateStr}
              showChips
              disabled={disabled}
            />
          </motion.div>
        ) : (
          <motion.div
            key="time"
            initial={{ opacity: 0, x: 12 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 12 }}
            transition={{ duration: 0.18 }}
            className="rounded-2xl bg-white/60 backdrop-blur-sm border border-white/70 shadow-sm p-4 space-y-4"
          >
            <div className="flex items-center gap-1.5 text-xs font-medium text-river/70">
              <Clock className="w-3.5 h-3.5" />
              <span>Select time</span>
            </div>

            {/* Three columns: Hour | Minute | AM-PM */}
            <div className="grid grid-cols-3 gap-2">
              {/* Hours */}
              <div className="space-y-1">
                <p className="text-center text-[10px] uppercase tracking-widest font-semibold text-river/40">
                  Hour
                </p>
                <div className="flex flex-col gap-0.5 max-h-48 overflow-y-auto scrollbar-hide rounded-xl bg-black/3 p-1">
                  {HOURS_12.map((h) => (
                    <button
                      key={h}
                      type="button"
                      onClick={() => setHour12(h)}
                      className={cn(
                        "py-1.5 rounded-lg text-sm font-medium transition-all duration-100",
                        hour12 === h
                          ? "bg-sage text-white shadow-sm"
                          : "text-charcoal/70 hover:bg-sage/10 hover:text-sage",
                      )}
                    >
                      {h}
                    </button>
                  ))}
                </div>
              </div>

              {/* Minutes */}
              <div className="space-y-1">
                <p className="text-center text-[10px] uppercase tracking-widest font-semibold text-river/40">
                  Min
                </p>
                <div className="flex flex-col gap-0.5 max-h-48 overflow-y-auto scrollbar-hide rounded-xl bg-black/3 p-1">
                  {MINUTES.map((m) => (
                    <button
                      key={m}
                      type="button"
                      onClick={() => setMinute(m)}
                      className={cn(
                        "py-1.5 rounded-lg text-sm font-medium transition-all duration-100",
                        minute === m
                          ? "bg-sage text-white shadow-sm"
                          : "text-charcoal/70 hover:bg-sage/10 hover:text-sage",
                      )}
                    >
                      {String(m).padStart(2, "0")}
                    </button>
                  ))}
                </div>
              </div>

              {/* AM / PM */}
              <div className="space-y-1">
                <p className="text-center text-[10px] uppercase tracking-widest font-semibold text-river/40">
                  Period
                </p>
                <div className="flex flex-col gap-1 rounded-xl bg-black/3 p-1">
                  {(["AM", "PM"] as const).map((p) => (
                    <button
                      key={p}
                      type="button"
                      onClick={() => setPeriod(p)}
                      className={cn(
                        "py-2.5 rounded-lg text-sm font-semibold transition-all duration-100",
                        period === p
                          ? "bg-terracotta text-white shadow-sm"
                          : "text-charcoal/60 hover:bg-terracotta/10 hover:text-terracotta",
                      )}
                    >
                      {p}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Confirm button */}
            <motion.button
              type="button"
              onClick={handleTimeConfirm}
              disabled={disabled}
              whileTap={{ scale: 0.97 }}
              className="w-full py-2.5 rounded-xl bg-sage text-white text-sm font-semibold shadow-sm hover:bg-sage-dark transition-colors disabled:opacity-40"
            >
              Confirm — {formatDateDisplay(dateStr)} at {timeDisplay}
            </motion.button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
