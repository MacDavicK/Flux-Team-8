import { AnimatePresence, motion } from "framer-motion";
import {
  Bell,
  CheckCircle2,
  Clock,
  LogOut,
  MessageCircle,
  Moon,
  Phone,
  Sun,
  Sunrise,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { apiFetch } from "~/lib/apiClient";
import {
  getPermissionState,
  registerAndSubscribe,
  unsubscribe as unsubscribePush,
} from "~/lib/pushNotifications";
import type { AccountMe, AccountPatchRequest } from "~/types";
import { cn } from "~/utils/cn";
import { EditField } from "./EditField";

const OTP_RESEND_COOLDOWN = 30;
const OTP_MAX_ATTEMPTS = 3;

interface ProfilePreferencesProps {
  account: AccountMe;
  onPatch: (patch: AccountPatchRequest) => Promise<void>;
  onLogout: () => void;
}

const CHRONOTYPE_ICONS = {
  morning: Sunrise,
  evening: Moon,
  neutral: Sun,
} as const;

const CHRONOTYPE_LABELS = {
  morning: "Morning person",
  evening: "Night owl",
  neutral: "Somewhere in between",
} as const;

interface PhoneVerificationFlowProps {
  onVerified: () => void;
  initialPhone?: string;
}

function PhoneVerificationFlow({
  onVerified,
  initialPhone = "",
}: PhoneVerificationFlowProps) {
  const [step, setStep] = useState<"phone" | "otp">("phone");
  const [phone, setPhone] = useState(initialPhone);
  const [phoneError, setPhoneError] = useState<string | null>(null);
  const [code, setCode] = useState("");
  const [codeError, setCodeError] = useState<string | null>(null);
  const [isSending, setIsSending] = useState(false);
  const [isVerifying, setIsVerifying] = useState(false);
  const [attempts, setAttempts] = useState(0);
  const [cooldown, setCooldown] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | undefined>(
    undefined,
  );

  function startCooldown() {
    setCooldown(OTP_RESEND_COOLDOWN);
    timerRef.current = setInterval(() => {
      setCooldown((s) => {
        if (s <= 1) {
          clearInterval(timerRef.current);
          return 0;
        }
        return s - 1;
      });
    }, 1000);
  }

  useEffect(() => () => clearInterval(timerRef.current), []);

  async function handleSendOtp() {
    const trimmed = phone.trim();
    if (!/^\+[1-9]\d{1,14}$/.test(trimmed)) {
      setPhoneError(
        "Enter your number in international format, e.g. +15551234567",
      );
      return;
    }
    setIsSending(true);
    setPhoneError(null);
    try {
      const res = await apiFetch("/api/v1/account/phone/verify/send", {
        method: "POST",
        body: JSON.stringify({ phone_number: trimmed }),
      });
      if (!res.ok) throw new Error();
      setStep("otp");
      startCooldown();
    } catch {
      setPhoneError("Couldn't send the code. Check the number and try again.");
    } finally {
      setIsSending(false);
    }
  }

  async function handleResend() {
    if (cooldown > 0) return;
    setIsSending(true);
    setCodeError(null);
    try {
      const res = await apiFetch("/api/v1/account/phone/verify/send", {
        method: "POST",
        body: JSON.stringify({ phone_number: phone.trim() }),
      });
      if (!res.ok) throw new Error();
      startCooldown();
    } catch {
      setCodeError("Couldn't resend. Try again.");
    } finally {
      setIsSending(false);
    }
  }

  async function handleVerify() {
    const trimmedCode = code.replace(/\D/g, "");
    if (trimmedCode.length !== 6) {
      setCodeError("Enter the 6-digit code from your SMS");
      return;
    }
    if (attempts >= OTP_MAX_ATTEMPTS) return;
    setIsVerifying(true);
    setCodeError(null);
    try {
      const res = await apiFetch("/api/v1/account/phone/verify/confirm", {
        method: "POST",
        body: JSON.stringify({ phone_number: phone.trim(), code: trimmedCode }),
      });
      if (res.ok) {
        onVerified();
        return;
      }
      const next = attempts + 1;
      setAttempts(next);
      if (next >= OTP_MAX_ATTEMPTS) {
        setCodeError("Too many incorrect attempts. Please try again later.");
      } else {
        setCodeError(
          `Incorrect code. ${OTP_MAX_ATTEMPTS - next} attempt${OTP_MAX_ATTEMPTS - next !== 1 ? "s" : ""} remaining.`,
        );
      }
    } catch {
      setCodeError("Verification failed. Try again.");
    } finally {
      setIsVerifying(false);
      setCode("");
    }
  }

  return (
    <div className="mt-3 space-y-3">
      {step === "phone" ? (
        <>
          <div className="flex gap-2">
            <input
              type="tel"
              value={phone}
              onChange={(e) => {
                setPhone(e.target.value);
                setPhoneError(null);
              }}
              onKeyDown={(e) => e.key === "Enter" && handleSendOtp()}
              placeholder="+15551234567"
              className={cn(
                "flex-1 px-3 py-2 text-sm rounded-xl border bg-white/90 text-charcoal",
                "placeholder:text-river/50 outline-none transition-colors",
                phoneError
                  ? "border-red-400 focus:border-red-500"
                  : "border-charcoal/20 focus:border-sage",
              )}
            />
            <button
              type="button"
              onClick={handleSendOtp}
              disabled={isSending || !phone.trim()}
              className="px-3 py-2 rounded-xl text-sm font-medium bg-sage text-white hover:bg-sage/90 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              {isSending ? "Sending…" : "Send code"}
            </button>
          </div>
          {phoneError && (
            <p className="text-red-500 text-xs pl-1">{phoneError}</p>
          )}
        </>
      ) : (
        <>
          <p className="text-xs text-river/60 pl-1">Code sent to {phone}</p>
          <div className="flex gap-2 items-center">
            <input
              type="text"
              inputMode="numeric"
              value={code}
              onChange={(e) => {
                setCode(e.target.value.replace(/\D/g, "").slice(0, 6));
                setCodeError(null);
              }}
              onKeyDown={(e) => e.key === "Enter" && handleVerify()}
              placeholder="000000"
              maxLength={6}
              disabled={attempts >= OTP_MAX_ATTEMPTS}
              className={cn(
                "w-32 px-3 py-2 text-sm rounded-xl border bg-white/90 text-charcoal text-center tracking-widest font-mono",
                "placeholder:text-river/40 outline-none transition-colors",
                codeError
                  ? "border-red-400 focus:border-red-500"
                  : "border-charcoal/20 focus:border-sage",
                "disabled:opacity-40 disabled:cursor-not-allowed",
              )}
            />
            <button
              type="button"
              onClick={handleVerify}
              disabled={
                isVerifying || code.length !== 6 || attempts >= OTP_MAX_ATTEMPTS
              }
              className="px-3 py-2 rounded-xl text-sm font-medium bg-sage text-white hover:bg-sage/90 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              {isVerifying ? "Checking…" : "Verify"}
            </button>
          </div>
          {codeError && (
            <p className="text-red-500 text-xs pl-1">{codeError}</p>
          )}
          <button
            type="button"
            onClick={handleResend}
            disabled={cooldown > 0 || isSending}
            className={cn(
              "text-xs pl-1 transition-colors",
              cooldown > 0 || isSending
                ? "text-river/40 cursor-not-allowed"
                : "text-sage hover:text-sage/80 underline underline-offset-2",
            )}
          >
            {isSending
              ? "Sending…"
              : cooldown > 0
                ? `Resend in ${cooldown}s`
                : "Resend code"}
          </button>
        </>
      )}
    </div>
  );
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="text-[10px] font-black uppercase tracking-[0.16em] text-river/60 mb-3 px-1">
      {children}
    </h3>
  );
}

export function ProfilePreferences({
  account,
  onPatch,
  onLogout,
}: ProfilePreferencesProps) {
  const [phoneVerified, setPhoneVerified] = useState(!!account.phone_verified);
  const [showVerifyFlow, setShowVerifyFlow] = useState(false);
  const notifPrefs = account.notification_preferences as {
    phone_number?: string;
    whatsapp_opted_in?: boolean;
    call_opted_in?: boolean;
  } | null;
  const savedPhone = notifPrefs?.phone_number ?? "";
  const [whatsappOptedIn, setWhatsappOptedIn] = useState(
    !!notifPrefs?.whatsapp_opted_in,
  );
  const [callOptedIn, setCallOptedIn] = useState(!!notifPrefs?.call_opted_in);
  const [togglingWhatsapp, setTogglingWhatsapp] = useState(false);
  const [togglingCall, setTogglingCall] = useState(false);
  const [pushEnabled, setPushEnabled] = useState(false);
  const [togglingPush, setTogglingPush] = useState(false);

  // Sync push state from browser permission after mount (SSR-safe)
  useEffect(() => {
    setPushEnabled(getPermissionState() === "granted");
  }, []);

  async function handleTogglePush() {
    if (togglingPush) return;
    setTogglingPush(true);
    try {
      if (!pushEnabled) {
        const success = await registerAndSubscribe();
        if (success) setPushEnabled(true);
      } else {
        await unsubscribePush();
        setPushEnabled(false);
      }
    } catch (err) {
      console.error("[push] Toggle failed:", err);
      // Don't update state on failure so the UI reflects reality
    } finally {
      setTogglingPush(false);
    }
  }

  async function handleToggleWhatsapp() {
    if (!phoneVerified || togglingWhatsapp) return;
    setTogglingWhatsapp(true);
    try {
      if (!whatsappOptedIn) {
        const res = await apiFetch("/api/v1/account/whatsapp/opt-in", {
          method: "POST",
        });
        if (res.ok) setWhatsappOptedIn(true);
      } else {
        await onPatch({
          notification_preferences: { whatsapp_opted_in: false },
        });
        setWhatsappOptedIn(false);
      }
    } finally {
      setTogglingWhatsapp(false);
    }
  }

  async function handleToggleCall() {
    if (!phoneVerified || togglingCall) return;
    setTogglingCall(true);
    try {
      await onPatch({
        notification_preferences: { call_opted_in: !callOptedIn },
      });
      setCallOptedIn((v) => !v);
    } finally {
      setTogglingCall(false);
    }
  }

  const profile = (account as AccountMe & { profile?: Record<string, unknown> })
    .profile as
    | {
        name?: string;
        sleep_window?: { start: string; end: string };
        work_hours?: string;
        chronotype?: string;
      }
    | undefined;

  const chronotype = (profile?.chronotype ?? "neutral") as
    | "morning"
    | "evening"
    | "neutral";
  const ChronotypeIcon = CHRONOTYPE_ICONS[chronotype] ?? Sun;

  return (
    <div className="space-y-6 px-5 pb-36">
      {/* ── Identity ──────────────────────────────────────────────── */}
      <motion.section
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
      >
        <SectionLabel>Identity</SectionLabel>
        <div className="glass-card p-4 space-y-4">
          <EditField
            label="Name"
            value={profile?.name ?? account.name ?? ""}
            placeholder="What should we call you?"
            onSave={async (name) => onPatch({ name })}
          />
          <EditField
            label="Email"
            value={account.email ?? ""}
            placeholder="your@email.com"
            onSave={async (email) => {
              void email;
            }}
            disabled
            hint="Managed by your auth provider"
          />
        </div>
      </motion.section>

      {/* ── Schedule ──────────────────────────────────────────────── */}
      <motion.section
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.15 }}
      >
        <SectionLabel>Schedule</SectionLabel>
        <div className="glass-card p-4 space-y-4">
          <EditField
            label="Timezone"
            value={account.timezone ?? "UTC"}
            placeholder="e.g. America/New_York"
            hint="Auto-detected from your browser"
            onSave={async () => {}}
            disabled
          />
          {profile?.sleep_window && (
            <div className="flex gap-3">
              <div className="flex-1">
                <EditField
                  label="Wake time"
                  value={profile.sleep_window.end ?? ""}
                  placeholder="07:00"
                  onSave={async () => {}}
                  disabled
                  hint="Set during onboarding"
                />
              </div>
              <div className="flex-1">
                <EditField
                  label="Sleep time"
                  value={profile.sleep_window.start ?? ""}
                  placeholder="23:00"
                  onSave={async () => {}}
                  disabled
                  hint="Set during onboarding"
                />
              </div>
            </div>
          )}
          {profile?.work_hours && (
            <EditField
              label="Work hours"
              value={profile.work_hours}
              onSave={async () => {}}
              disabled
              hint="Set during onboarding"
            />
          )}
        </div>
      </motion.section>

      {/* ── Vibe ──────────────────────────────────────────────────── */}
      {profile?.chronotype && (
        <motion.section
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
        >
          <SectionLabel>Energy Rhythm</SectionLabel>
          <div className="glass-card p-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl fab-gradient flex items-center justify-center shrink-0">
                <ChronotypeIcon className="w-5 h-5 text-white" />
              </div>
              <div>
                <p className="text-sm font-semibold text-charcoal">
                  {CHRONOTYPE_LABELS[chronotype]}
                </p>
                <p className="text-xs text-river/60 mt-0.5">
                  Your chronotype guides task scheduling
                </p>
              </div>
            </div>
          </div>
        </motion.section>
      )}

      {/* ── Notifications ─────────────────────────────────────────── */}
      <motion.section
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.25 }}
      >
        <SectionLabel>Notifications</SectionLabel>
        <div className="glass-card p-4 space-y-4">
          {/* Phone verification row */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl glass-bubble flex items-center justify-center shrink-0">
              {phoneVerified ? (
                <Bell className="w-5 h-5 text-sage" />
              ) : (
                <Clock className="w-5 h-5 text-river/60" />
              )}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-charcoal">
                {phoneVerified ? "Phone verified" : "Phone not verified"}
              </p>
              <p className="text-xs text-river/60 mt-0.5">
                {savedPhone
                  ? savedPhone
                  : phoneVerified
                    ? "You'll receive reminders via SMS"
                    : "Verify your number to enable reminders"}
              </p>
            </div>
            {phoneVerified ? (
              <CheckCircle2 className="w-5 h-5 text-sage shrink-0" />
            ) : (
              <button
                type="button"
                onClick={() => setShowVerifyFlow((v) => !v)}
                className="text-xs font-semibold text-sage hover:text-sage/80 shrink-0 transition-colors"
              >
                {showVerifyFlow ? "Cancel" : "Verify now"}
              </button>
            )}
          </div>
          <AnimatePresence>
            {!phoneVerified && showVerifyFlow && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.2 }}
                className="overflow-hidden"
              >
                <PhoneVerificationFlow
                  initialPhone={savedPhone}
                  onVerified={() => {
                    setPhoneVerified(true);
                    setShowVerifyFlow(false);
                  }}
                />
              </motion.div>
            )}
          </AnimatePresence>

          {/* Phone number field (when verified) */}
          {phoneVerified && savedPhone && (
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-2xl glass-bubble flex items-center justify-center shrink-0">
                <Phone className="w-5 h-5 text-river/60" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-[10px] font-semibold uppercase tracking-widest text-river/70 mb-0.5">
                  Phone number
                </p>
                <p className="text-sm text-charcoal">{savedPhone}</p>
              </div>
            </div>
          )}

          {/* Push notifications */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl glass-bubble flex items-center justify-center shrink-0">
              <Bell className="w-5 h-5 text-river/60" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-charcoal">
                Push notifications
              </p>
              <p className="text-xs text-river/60 mt-0.5">
                {pushEnabled
                  ? "Browser notifications enabled"
                  : "Get notified right in your browser"}
              </p>
            </div>
            <button
              type="button"
              onClick={handleTogglePush}
              disabled={togglingPush}
              className={cn(
                "relative w-11 h-6 rounded-full transition-colors duration-200 shrink-0",
                "focus:outline-none disabled:cursor-not-allowed",
                pushEnabled ? "bg-sage" : "bg-river/20",
              )}
              aria-label={
                pushEnabled
                  ? "Disable push notifications"
                  : "Enable push notifications"
              }
            >
              <span
                className={cn(
                  "absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform duration-200",
                  pushEnabled && "translate-x-5",
                )}
              />
            </button>
          </div>

          {/* WhatsApp opt-in */}
          <div
            className={cn(
              "flex items-center gap-3",
              !phoneVerified && "opacity-50",
            )}
          >
            <div className="w-10 h-10 rounded-2xl glass-bubble flex items-center justify-center shrink-0">
              <MessageCircle className="w-5 h-5 text-river/60" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-charcoal">
                WhatsApp reminders
              </p>
              <p className="text-xs text-river/60 mt-0.5">
                {phoneVerified
                  ? "Receive reminders via WhatsApp"
                  : "Verify your phone to enable"}
              </p>
            </div>
            <button
              type="button"
              onClick={handleToggleWhatsapp}
              disabled={!phoneVerified || togglingWhatsapp}
              className={cn(
                "relative w-11 h-6 rounded-full transition-colors duration-200 shrink-0",
                "focus:outline-none disabled:cursor-not-allowed",
                whatsappOptedIn ? "bg-sage" : "bg-river/20",
              )}
              aria-label={
                whatsappOptedIn
                  ? "Disable WhatsApp reminders"
                  : "Enable WhatsApp reminders"
              }
            >
              <span
                className={cn(
                  "absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform duration-200",
                  whatsappOptedIn && "translate-x-5",
                )}
              />
            </button>
          </div>

          {/* Call opt-in */}
          <div
            className={cn(
              "flex items-center gap-3",
              !phoneVerified && "opacity-50",
            )}
          >
            <div className="w-10 h-10 rounded-2xl glass-bubble flex items-center justify-center shrink-0">
              <Phone className="w-5 h-5 text-river/60" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-charcoal">
                Phone call reminders
              </p>
              <p className="text-xs text-river/60 mt-0.5">
                {phoneVerified
                  ? "Receive reminders via phone call"
                  : "Verify your phone to enable"}
              </p>
            </div>
            <button
              type="button"
              onClick={handleToggleCall}
              disabled={!phoneVerified || togglingCall}
              className={cn(
                "relative w-11 h-6 rounded-full transition-colors duration-200 shrink-0",
                "focus:outline-none disabled:cursor-not-allowed",
                callOptedIn ? "bg-sage" : "bg-river/20",
              )}
              aria-label={
                callOptedIn ? "Disable call reminders" : "Enable call reminders"
              }
            >
              <span
                className={cn(
                  "absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white shadow transition-transform duration-200",
                  callOptedIn && "translate-x-5",
                )}
              />
            </button>
          </div>
        </div>
      </motion.section>

      {/* ── Sign out ──────────────────────────────────────────────── */}
      <motion.section
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
      >
        <motion.button
          onClick={onLogout}
          whileTap={{ scale: 0.97 }}
          className="w-full glass-card p-4 flex items-center gap-3 text-left group hover:bg-terracotta/10 transition-colors duration-200 active:scale-[0.98]"
        >
          <div className="w-10 h-10 rounded-2xl bg-terracotta/10 flex items-center justify-center shrink-0 group-hover:bg-terracotta/20 transition-colors">
            <LogOut className="w-5 h-5 text-terracotta" />
          </div>
          <span className="text-sm font-semibold text-terracotta">
            Sign out
          </span>
        </motion.button>
      </motion.section>
    </div>
  );
}
