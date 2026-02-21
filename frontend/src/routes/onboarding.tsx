import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { AnimatePresence, motion } from "framer-motion";
import { useCallback, useEffect, useRef, useState } from "react";
import { ChatBubble } from "~/components/chat/ChatBubble";
import { ChatInput } from "~/components/chat/ChatInput";
import { ThinkingIndicator } from "~/components/chat/ThinkingIndicator";
import { AmbientBackground } from "~/components/ui/AmbientBackground";
import { useAuth } from "~/contexts/AuthContext";
import { onboardingService } from "~/services/OnboardingService";
import type { OnboardingProfile, OnboardingStep } from "~/types";
import { MessageVariant } from "~/types/message";

export const Route = createFileRoute("/onboarding")({
  component: OnboardingPage,
});

interface OnboardingMessage {
  id: string;
  content: string | React.ReactNode;
  type: MessageVariant;
}

const INITIAL_MESSAGE: OnboardingMessage = {
  id: "1",
  content: "Welcome to Flux! What should I call you?",
  type: MessageVariant.AI,
};

function OnboardingPage() {
  const navigate = useNavigate();
  const { isAuthenticated, isLoading: authLoading, user } = useAuth();
  const [messages, setMessages] = useState<OnboardingMessage[]>([
    INITIAL_MESSAGE,
  ]);
  const [isThinking, setIsThinking] = useState(false);
  const [currentProfile, setCurrentProfile] = useState<
    Partial<OnboardingProfile>
  >({});
  const [currentStep, setCurrentStep] = useState<OnboardingStep>("name");

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [scrollToBottom]);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      navigate({ to: "/login" });
    }
  }, [authLoading, isAuthenticated, navigate]);

  const handleSendMessage = async (text: string) => {
    const userMessage: OnboardingMessage = {
      id: Date.now().toString(),
      content: text,
      type: MessageVariant.USER,
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsThinking(true);

    try {
      const response = await onboardingService.sendMessage(
        text,
        currentProfile,
      );

      setTimeout(() => {
        setIsThinking(false);

        const aiMessage: OnboardingMessage = {
          id: (Date.now() + 1).toString(),
          content: response.message,
          type: MessageVariant.AI,
        };

        setMessages((prev) => [...prev, aiMessage]);
        setCurrentProfile(response.profile);
        setCurrentStep(response.nextStep);

        if (response.isComplete) {
          const completeProfile: OnboardingProfile = {
            name: response.profile.name || user?.name || "User",
            sleep_window: response.profile.sleep_window || {
              start: "23:00",
              end: "07:00",
            },
            work_hours: response.profile.work_hours || {
              start: "09:00",
              end: "18:00",
              days: ["Mon", "Tue", "Wed", "Thu", "Fri"],
            },
            chronotype: response.profile.chronotype || "neutral",
            existing_commitments: response.profile.existing_commitments || [],
            locations: response.profile.locations || {
              home: "Home",
              work: "Work",
            },
          };

          onboardingService.complete(completeProfile).then(() => {
            const completeMessage: OnboardingMessage = {
              id: (Date.now() + 2).toString(),
              content:
                "Your profile is all set! Let's start planning your goals.",
              type: MessageVariant.AI,
            };
            setMessages((prev) => [...prev, completeMessage]);

            setTimeout(() => {
              navigate({ to: "/" });
            }, 1500);
          });
        }
      }, 800);
    } catch (_error) {
      setIsThinking(false);
      const errorMessage: OnboardingMessage = {
        id: (Date.now() + 1).toString(),
        content:
          "Sorry, I had trouble understanding that. Could you try again?",
        type: MessageVariant.AI,
      };
      setMessages((prev) => [...prev, errorMessage]);
    }
  };

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-pulse text-sage">Loading...</div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="min-h-screen pb-56">
      <AmbientBackground variant="dark" />

      <div className="px-4 pt-6 space-y-4">
        <AnimatePresence mode="popLayout">
          {messages.map((message, index) => (
            <motion.div
              key={message.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ delay: index * 0.05 }}
              className={
                message.type === MessageVariant.USER ? "flex justify-end" : ""
              }
            >
              <ChatBubble variant={message.type} animate={false}>
                {message.content}
              </ChatBubble>
            </motion.div>
          ))}
        </AnimatePresence>

        {isThinking && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <ChatBubble variant={MessageVariant.AI} animate={false}>
              <ThinkingIndicator />
            </ChatBubble>
          </motion.div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <ChatInput
        onSend={handleSendMessage}
        disabled={isThinking || currentStep === "complete"}
        placeholder={
          currentStep === "name"
            ? "Enter your name..."
            : currentStep === "wake_time"
              ? "e.g., 7:00 AM"
              : currentStep === "sleep_time"
                ? "e.g., 11:00 PM"
                : currentStep === "work_schedule"
                  ? "e.g., 9am-5pm or 'no'"
                  : currentStep === "chronotype"
                    ? "Morning person or night owl?"
                    : currentStep === "locations"
                      ? "Home and work locations..."
                      : currentStep === "existing_commitments"
                        ? "Any regular commitments?"
                        : "What's on your mind?"
        }
      />
    </div>
  );
}
