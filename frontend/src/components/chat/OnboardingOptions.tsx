import { AnimatePresence, motion } from "framer-motion";
import { useEffect, useRef, useState } from "react";
import { chatService } from "~/services/ChatService";
import type { OnboardingOption } from "~/types";
import { cn } from "~/utils/cn";

interface OnboardingOptionsProps {
  options: OnboardingOption[];
  onSelect: (value: string) => void;
  disabled?: boolean;
  phoneNumber?: string; // required for the OTP resend button
}

/**
 * Validates a value against the zod_validator string sent from the backend.
 *
 * We parse two patterns (all the backend ever sends):
 *   z.string().regex(/.../, "msg")
 *   z.string().min(n, "msg").max(m, "msg")   (max is optional)
 *
 * Returns null on success, or the error message string on failure.
 */
function validate(value: string, zodStr: string): string | null {
  // .min(n, "msg")
  const minMatch = zodStr.match(/\.min\((\d+),\s*"([^"]+)"\)/);
  if (minMatch && value.length < Number(minMatch[1])) return minMatch[2];

  // .max(n, "msg")
  const maxMatch = zodStr.match(/\.max\((\d+),\s*"([^"]+)"\)/);
  if (maxMatch && value.length > Number(maxMatch[1])) return maxMatch[2];

  // .regex(/pattern/flags, "msg")
  const regexMatch = zodStr.match(/\.regex\(\/(.+?)\/([gimsuy]*),\s*"([^"]+)"\)/);
  if (regexMatch) {
    const re = new RegExp(regexMatch[1], regexMatch[2]);
    if (!re.test(value)) return regexMatch[3];
  }

  return null;
}

const OTP_RESEND_COOLDOWN = 30; // seconds — industry standard (Twilio/Authy)
const OTP_MAX_ATTEMPTS = 3;

interface OtpInputProps {
  phoneNumber: string;
  onSubmit: (code: string) => void;
  disabled?: boolean;
}

function OtpInput({ phoneNumber, onSubmit, disabled }: OtpInputProps) {
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [attempts, setAttempts] = useState(0);
  const [cooldown, setCooldown] = useState(OTP_RESEND_COOLDOWN);
  const [isResending, setIsResending] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Start cooldown timer on mount (OTP was just sent by the backend)
  useEffect(() => {
    timerRef.current = setInterval(() => {
      setCooldown((s) => {
        if (s <= 1) {
          clearInterval(timerRef.current!);
          return 0;
        }
        return s - 1;
      });
    }, 1000);
    return () => clearInterval(timerRef.current!);
  }, []);

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const val = e.target.value.replace(/\D/g, "").slice(0, 6);
    setCode(val);
    setError(null);
  }

  function handleSubmit() {
    if (disabled || attempts >= OTP_MAX_ATTEMPTS) return;
    if (code.length !== 6) {
      setError("Enter the 6-digit code from your SMS");
      return;
    }
    const next = attempts + 1;
    setAttempts(next);
    onSubmit(code);
    setCode("");
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") handleSubmit();
  }

  async function handleResend() {
    if (cooldown > 0 || isResending || !phoneNumber) return;
    setIsResending(true);
    setError(null);
    try {
      await chatService.resendOtp(phoneNumber);
      // Reset cooldown
      setCooldown(OTP_RESEND_COOLDOWN);
      timerRef.current = setInterval(() => {
        setCooldown((s) => {
          if (s <= 1) {
            clearInterval(timerRef.current!);
            return 0;
          }
          return s - 1;
        });
      }, 1000);
    } catch {
      setError("Couldn't resend the code. Try again.");
    } finally {
      setIsResending(false);
    }
  }

  const attemptsLeft = OTP_MAX_ATTEMPTS - attempts;

  return (
    <div className="mt-3 space-y-2">
      <div className="flex gap-2 items-center">
        <input
          type="text"
          inputMode="numeric"
          pattern="\d*"
          value={code}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder="000000"
          maxLength={6}
          disabled={disabled || attempts >= OTP_MAX_ATTEMPTS}
          autoFocus
          className={cn(
            "w-36 px-3 py-2 text-sm rounded-xl border bg-white/90 text-charcoal text-center tracking-widest font-mono",
            "placeholder:text-river/40 outline-none transition-colors",
            error
              ? "border-red-400 focus:border-red-500"
              : "border-charcoal/20 focus:border-sage",
            "disabled:opacity-40 disabled:cursor-not-allowed",
          )}
        />
        <button
          type="button"
          onClick={handleSubmit}
          disabled={disabled || code.length !== 6 || attempts >= OTP_MAX_ATTEMPTS}
          className={cn(
            "px-3 py-2 rounded-xl text-sm font-medium transition-colors",
            "bg-terracotta text-white",
            "hover:bg-terracotta/90 disabled:opacity-40 disabled:cursor-not-allowed",
          )}
        >
          Verify
        </button>
      </div>

      {error && <p className="text-red-500 text-xs pl-1">{error}</p>}

      {attempts > 0 && attemptsLeft > 0 && !error && (
        <p className="text-river/60 text-xs pl-1">
          {attemptsLeft} attempt{attemptsLeft !== 1 ? "s" : ""} remaining
        </p>
      )}

      <button
        type="button"
        onClick={handleResend}
        disabled={cooldown > 0 || isResending}
        className={cn(
          "text-xs transition-colors pl-1",
          cooldown > 0 || isResending
            ? "text-river/40 cursor-not-allowed"
            : "text-sage hover:text-sage/80 underline underline-offset-2",
        )}
      >
        {isResending
          ? "Sending…"
          : cooldown > 0
            ? `Resend code in ${cooldown}s`
            : "Resend code"}
      </button>
    </div>
  );
}

export function OnboardingOptions({ options, onSelect, disabled, phoneNumber = "" }: OnboardingOptionsProps) {
  const [specifyStep, setSpecifyStep] = useState<OnboardingOption | null>(null);
  const [specifyValue, setSpecifyValue] = useState("");
  const [specifyError, setSpecifyError] = useState<string | null>(null);
  const [datetimeStep, setDatetimeStep] = useState(false);
  const [datetimeValue, setDatetimeValue] = useState("");

  // OTP step: render the dedicated OTP widget
  const otpOption = options.find((o) => o.input_type === "otp");
  if (otpOption) {
    return <OtpInput phoneNumber={phoneNumber} onSubmit={onSelect} disabled={disabled} />;
  }

  const datetimeOption = options.find((o) => o.input_type === "datetime");
  const specifyOption = options.find((o) => o.value === null && o.input_type !== "datetime");
  const regularOptions = options.filter((o) => o.value !== null);

  function handleOptionClick(option: OnboardingOption) {
    if (disabled) return;
    if (option.value === null) {
      // "Specify" — open text input
      setSpecifyStep(option);
      setSpecifyValue("");
      setSpecifyError(null);
    } else {
      onSelect(option.value);
    }
  }

  function handleSpecifySubmit() {
    if (!specifyStep || disabled) return;

    const trimmed = specifyValue.trim();
    if (!trimmed) {
      setSpecifyError("Please enter a value");
      return;
    }

    if (specifyStep.zod_validator) {
      const error = validate(trimmed, specifyStep.zod_validator);
      if (error) {
        setSpecifyError(error);
        return;
      }
    }

    onSelect(trimmed);
    setSpecifyStep(null);
    setSpecifyValue("");
    setSpecifyError(null);
  }

  function handleSpecifyKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") handleSpecifySubmit();
    if (e.key === "Escape") {
      setSpecifyStep(null);
      setSpecifyValue("");
      setSpecifyError(null);
    }
  }

  function handleDatetimeSubmit() {
    if (!datetimeValue || disabled) return;
    // Convert local datetime string (YYYY-MM-DDTHH:mm) to UTC ISO for the slot-confirm path
    const isoUtc = new Date(datetimeValue).toISOString();
    setDatetimeStep(false);
    setDatetimeValue("");
    onSelect(isoUtc);
  }

  function handleDatetimeKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter") handleDatetimeSubmit();
    if (e.key === "Escape") { setDatetimeStep(false); setDatetimeValue(""); }
  }

  // Compute min for datetime-local input: now rounded up to the next minute
  const nowLocal = new Date(Date.now() - new Date().getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 16);

  return (
    <div className="mt-3 space-y-2">
      <div className="flex flex-wrap gap-2">
        {regularOptions.map((opt) => (
          <motion.button
            key={opt.label}
            type="button"
            onClick={() => handleOptionClick(opt)}
            disabled={disabled}
            whileTap={{ scale: 0.96 }}
            className={cn(
              "px-3 py-1.5 rounded-full text-sm font-medium border transition-colors",
              "bg-white/80 border-charcoal/20 text-charcoal",
              "hover:bg-sage/10 hover:border-sage active:bg-sage/20",
              "disabled:opacity-40 disabled:cursor-not-allowed",
            )}
          >
            {opt.label}
          </motion.button>
        ))}

        {specifyOption && !specifyStep && (
          <motion.button
            key="specify"
            type="button"
            onClick={() => handleOptionClick(specifyOption)}
            disabled={disabled}
            whileTap={{ scale: 0.96 }}
            className={cn(
              "px-3 py-1.5 rounded-full text-sm font-medium border transition-colors",
              "bg-terracotta/10 border-terracotta/30 text-terracotta",
              "hover:bg-terracotta/20 hover:border-terracotta/50",
              "disabled:opacity-40 disabled:cursor-not-allowed",
            )}
          >
            {specifyOption.label}
          </motion.button>
        )}

        {datetimeOption && !datetimeStep && (
          <motion.button
            key="datetime"
            type="button"
            onClick={() => { setDatetimeStep(true); setDatetimeValue(""); }}
            disabled={disabled}
            whileTap={{ scale: 0.96 }}
            className={cn(
              "px-3 py-1.5 rounded-full text-sm font-medium border transition-colors",
              "bg-terracotta/10 border-terracotta/30 text-terracotta",
              "hover:bg-terracotta/20 hover:border-terracotta/50",
              "disabled:opacity-40 disabled:cursor-not-allowed",
            )}
          >
            {datetimeOption.label}
          </motion.button>
        )}
      </div>

      <AnimatePresence>
        {specifyStep && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="flex gap-2 items-center pt-1">
              <input
                type={specifyStep?.zod_validator?.includes("\\+[1-9]") ? "tel" : "text"}
                value={specifyValue}
                onChange={(e) => {
                  setSpecifyValue(e.target.value);
                  setSpecifyError(null);
                }}
                onKeyDown={handleSpecifyKeyDown}
                placeholder={specifyStep?.zod_validator?.includes("\\+[1-9]") ? "+1 555 123 4567" : "Type your answer…"}
                disabled={disabled}
                autoFocus
                className={cn(
                  "flex-1 px-3 py-2 text-sm rounded-xl border bg-white/90 text-charcoal",
                  "placeholder:text-river/50 outline-none transition-colors",
                  specifyError
                    ? "border-red-400 focus:border-red-500"
                    : "border-charcoal/20 focus:border-sage",
                )}
              />
              <button
                type="button"
                onClick={handleSpecifySubmit}
                disabled={disabled || !specifyValue.trim()}
                className={cn(
                  "px-3 py-2 rounded-xl text-sm font-medium transition-colors",
                  "bg-terracotta text-white",
                  "hover:bg-terracotta/90 disabled:opacity-40 disabled:cursor-not-allowed",
                )}
              >
                OK
              </button>
            </div>
            {specifyError && (
              <p className="text-red-500 text-xs mt-1 pl-1">{specifyError}</p>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {datetimeStep && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="flex gap-2 items-center pt-1">
              <input
                type="datetime-local"
                value={datetimeValue}
                min={nowLocal}
                onChange={(e) => setDatetimeValue(e.target.value)}
                onKeyDown={handleDatetimeKeyDown}
                disabled={disabled}
                autoFocus
                className={cn(
                  "flex-1 px-3 py-2 text-sm rounded-xl border bg-white/90 text-charcoal",
                  "outline-none transition-colors border-charcoal/20 focus:border-sage",
                  "disabled:opacity-40 disabled:cursor-not-allowed",
                )}
              />
              <button
                type="button"
                onClick={handleDatetimeSubmit}
                disabled={disabled || !datetimeValue}
                className={cn(
                  "px-3 py-2 rounded-xl text-sm font-medium transition-colors",
                  "bg-terracotta text-white",
                  "hover:bg-terracotta/90 disabled:opacity-40 disabled:cursor-not-allowed",
                )}
              >
                OK
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
