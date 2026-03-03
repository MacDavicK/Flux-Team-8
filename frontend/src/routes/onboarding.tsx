import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle2 } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { ChatBubble } from "~/components/chat/ChatBubble";
import { ChatInput } from "~/components/chat/ChatInput";
import { ThinkingIndicator } from "~/components/chat/ThinkingIndicator";
import { AmbientBackground } from "~/components/ui/AmbientBackground";
import { useAuth } from "~/contexts/AuthContext";
import { MessageVariant } from "~/types/message";
import { api } from "~/utils/api";

const STATE_PLACEHOLDERS: Record<string, string> = {
  ASK_NAME: "Your name...",
  ASK_WAKE_TIME: "e.g., 7am, 07:00...",
  ASK_SLEEP_TIME: "e.g., 11pm, 23:00...",
  ASK_WORK_SCHEDULE: "e.g., 9-5 Mon-Fri, or 'no'...",
  ASK_CHRONOTYPE: "Morning person / Night owl...",
  ASK_COMMITMENTS: "e.g., Gym on Tuesdays at 7pm, or 'none'...",
};

interface OnboardingMessage {
  id: string;
  type: MessageVariant;
  content: string;
}

export const Route = createFileRoute("/onboarding")({
  component: OnboardingPage,
});

function OnboardingPage() {
  const navigate = useNavigate();
  const { user, refreshAuthStatus, isLoading: authLoading } = useAuth();
  const [messages, setMessages] = useState<OnboardingMessage[]>([]);

  useEffect(() => {
    if (authLoading) return;
    if (user?.onboarded) {
      navigate({ to: "/" });
    }
  }, [authLoading, user?.onboarded, navigate]);
  const [isThinking, setIsThinking] = useState(false);
  const [progress, setProgress] = useState(0);
  const [lastState, setLastState] = useState<string | undefined>();
  const [error, setError] = useState<string | null>(null);
  const [showCelebration, setShowCelebration] = useState(false);
  const initDoneRef = useRef(false);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const scrollToBottom = useCallback(() => {
    setTimeout(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, 50);
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [scrollToBottom]);

  // Initial load: get first message (resume or greeting)
  useEffect(() => {
    if (initDoneRef.current || error) return;
    initDoneRef.current = true;
    setError(null);
    setIsThinking(true);
    api
      .onboardingChat("")
      .then((res) => {
        setMessages([
          {
            id: "welcome",
            type: MessageVariant.AI,
            content: res.message,
          },
        ]);
        const status = res as { state?: string; progress?: number };
        if (typeof status.progress === "number") setProgress(status.progress);
        if (status.state) setLastState(status.state);
        setTimeout(() => scrollToBottom(), 80);
      })
      .catch(() => {
        setError(
          "Can't connect to Flux right now. Please check your connection and try again.",
        );
      })
      .finally(() => {
        setIsThinking(false);
      });
  }, [error, scrollToBottom]);

  const handleSendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || isThinking) return;
      setError(null);
      const userMsg: OnboardingMessage = {
        id: `user-${Date.now()}`,
        type: MessageVariant.USER,
        content: text.trim(),
      };
      setMessages((prev) => [...prev, userMsg]);
      setIsThinking(true);
      setTimeout(() => scrollToBottom(), 80);

      try {
        const res = await api.onboardingChat(text.trim());
        const aiMsg: OnboardingMessage = {
          id: `ai-${Date.now()}`,
          type: MessageVariant.AI,
          content: res.message,
        };
        setMessages((prev) => [...prev, aiMsg]);
        setTimeout(() => scrollToBottom(), 80);
        const extended = res as {
          state?: string;
          progress?: number;
          is_complete?: boolean;
        };
        if (typeof extended.progress === "number")
          setProgress(extended.progress);
        if (extended.state) setLastState(extended.state);

        const updated = await refreshAuthStatus();
        if (extended.is_complete === true || updated?.onboarded) {
          setShowCelebration(true);
          setTimeout(() => {
            navigate({ to: "/" });
          }, 2000);
        }
      } catch {
        setError(
          "Can't connect to Flux right now. Please check your connection and try again.",
        );
      } finally {
        setIsThinking(false);
        scrollToBottom();
      }
    },
    [isThinking, refreshAuthStatus, navigate, scrollToBottom],
  );

  const handleRetry = useCallback(() => {
    setError(null);
    initDoneRef.current = false;
  }, []);

  const placeholder =
    (lastState && STATE_PLACEHOLDERS[lastState]) ?? "Your answer...";

  if (showCelebration) {
    return (
      <div className="relative min-h-screen flex flex-col items-center justify-center">
        <AmbientBackground variant="light" />
        <motion.div
          className="relative z-10 flex flex-col items-center gap-4"
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.4 }}
        >
          <motion.div
            animate={{ scale: [1, 1.1, 1] }}
            transition={{ duration: 0.6, repeat: 1 }}
            className="w-20 h-20 rounded-full bg-sage/20 flex items-center justify-center"
          >
            <CheckCircle2 className="w-12 h-12 text-sage" />
          </motion.div>
          <p className="font-display italic text-xl text-charcoal">
            You&apos;re all set!
          </p>
          <p className="text-river/80 text-sm">Taking you to your flow...</p>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="relative h-screen flex flex-col overflow-hidden">
      <AmbientBackground variant="light" />

      {/* Progress */}
      <div className="relative z-10 px-5 pt-12 pb-3">
        <p className="text-sm text-river/80 mb-2">Setting up your profile</p>
        <div className="h-2 rounded-full bg-white/40 overflow-hidden">
          <motion.div
            className="h-full rounded-full bg-sage"
            initial={{ width: 0 }}
            animate={{ width: `${Math.min(100, progress * 100)}%` }}
            transition={{ duration: 0.3 }}
          />
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 pt-2 space-y-4 pb-4 relative z-10">
        {error ? (
          <div className="glass-card p-4 rounded-2xl space-y-3">
            <p className="text-sm text-charcoal">{error}</p>
            <button
              type="button"
              onClick={handleRetry}
              className="px-4 py-2 rounded-full bg-sage text-white text-sm font-medium hover:bg-sage-dark transition-colors"
            >
              Retry
            </button>
          </div>
        ) : (
          <>
            <AnimatePresence mode="popLayout">
              {messages.map((message, index) => (
                <motion.div
                  key={message.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ delay: index * 0.05 }}
                  className={
                    message.type === MessageVariant.USER
                      ? "flex justify-end"
                      : ""
                  }
                >
                  <ChatBubble variant={message.type} animate={false}>
                    <span className="text-base leading-relaxed">
                      {message.content}
                    </span>
                  </ChatBubble>
                </motion.div>
              ))}
            </AnimatePresence>

            {isThinking && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="flex justify-start"
              >
                <ChatBubble variant={MessageVariant.AI} animate={false}>
                  <ThinkingIndicator />
                </ChatBubble>
              </motion.div>
            )}

            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {!error && (
        <div className="relative z-10">
          <ChatInput
            onSend={handleSendMessage}
            disabled={isThinking}
            placeholder={placeholder}
          />
        </div>
      )}
    </div>
  );
}
