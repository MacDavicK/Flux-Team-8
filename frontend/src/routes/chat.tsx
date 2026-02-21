import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { AnimatePresence, motion } from "framer-motion";
import { useCallback, useEffect, useRef, useState } from "react";
import { ChatBubble } from "~/components/chat/ChatBubble";
import { ChatInput } from "~/components/chat/ChatInput";
import { PlanView } from "~/components/chat/PlanView";
import { ThinkingIndicator } from "~/components/chat/ThinkingIndicator";
import { BottomNav } from "~/components/navigation/BottomNav";
import { AmbientBackground } from "~/components/ui/AmbientBackground";
import { useAuth } from "~/contexts/AuthContext";
import { useSimulation } from "~/contexts/SimulationContext";
import { goalPlannerService } from "~/services/GoalPlannerService";
import { onboardingService } from "~/services/OnboardingService";
import type {
  ChatMessage,
  GoalContext,
  OnboardingProfile,
  OnboardingStep,
  PlanMilestone,
} from "~/types";
import { AgentState } from "~/types/goal";
import { MessageVariant } from "~/types/message";

const INITIAL_CHAT_MESSAGE: ChatMessage = {
  id: "1",
  type: MessageVariant.AI,
  content:
    "Hi! I'm here to help you break down your goals into manageable tasks. What would you like to achieve?",
};

const INITIAL_ONBOARDING_MESSAGE: ChatMessage = {
  id: "1",
  type: MessageVariant.AI,
  content: "Welcome to Flux! What should I call you?",
};

export const Route = createFileRoute("/chat")({
  component: ChatPage,
});

function ChatPage() {
  const navigate = useNavigate();
  const { isAuthenticated, isLoading: authLoading, user } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isThinking, setIsThinking] = useState(false);
  const [agentState, setAgentState] = useState<AgentState>(AgentState.IDLE);
  const [goalContext, setGoalContext] = useState<GoalContext>({});
  const [currentProfile, setCurrentProfile] = useState<
    Partial<OnboardingProfile>
  >({});
  const [currentStep, setCurrentStep] = useState<OnboardingStep>("name");

  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const { stopEscalation } = useSimulation();

  const isOnboarding = user && !user.onboarded;

  const scrollToBottom = useCallback(() => {
    setTimeout(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, 50);
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [scrollToBottom]);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      navigate({ to: "/login" });
    }
  }, [authLoading, isAuthenticated, navigate]);

  useEffect(() => {
    if (!authLoading && messages.length === 0) {
      if (isOnboarding) {
        setMessages([INITIAL_ONBOARDING_MESSAGE]);
      } else if (isAuthenticated) {
        setMessages([INITIAL_CHAT_MESSAGE]);
      }
    }
  }, [authLoading, isOnboarding, isAuthenticated, messages.length]);

  const handleSendMessage = async (text: string) => {
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      type: MessageVariant.USER,
      content: text,
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsThinking(true);
    scrollToBottom();

    stopEscalation();

    if (isOnboarding) {
      await handleOnboardingMessage(text);
    } else {
      await handleChatMessage(text);
    }
  };

  const handleOnboardingMessage = async (text: string) => {
    try {
      const response = await onboardingService.sendMessage(
        text,
        currentProfile,
      );

      setTimeout(() => {
        setIsThinking(false);

        const aiMessage: ChatMessage = {
          id: (Date.now() + 1).toString(),
          type: MessageVariant.AI,
          content: response.message,
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
            const completeMessage: ChatMessage = {
              id: (Date.now() + 2).toString(),
              type: MessageVariant.AI,
              content:
                "Your profile is all set! Let's start planning your goals.",
            };
            setMessages((prev) => [...prev, completeMessage]);

            setTimeout(() => {
              navigate({ to: "/" });
            }, 1500);
          });
        }
      }, 800);
    } catch {
      setIsThinking(false);
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        type: MessageVariant.AI,
        content:
          "Sorry, I had trouble understanding that. Could you try again?",
      };
      setMessages((prev) => [...prev, errorMessage]);
    }
  };

  const handleChatMessage = async (text: string) => {
    const result = await goalPlannerService.sendMessage(
      text,
      agentState,
      goalContext,
    );
    const response = result.response;
    setAgentState(result.newState as AgentState);
    setGoalContext(result.newContext);

    setTimeout(() => {
      setIsThinking(false);

      if (!response) return;

      const aiMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        type: MessageVariant.AI,
        content: (
          <div className="space-y-3">
            <p>{response.message}</p>
            {response.type === "plan" && response.plan && (
              <PlanView
                plan={response.plan as PlanMilestone[]}
                onConfirm={() => handleSendMessage("Yes, this looks great!")}
              />
            )}
            {response.suggestedAction && (
              <button
                type="button"
                onClick={() => {
                  if (response.suggestedAction) {
                    handleSendMessage(response.suggestedAction);
                  }
                }}
                className="text-sage font-medium text-sm hover:underline"
              >
                {response.suggestedAction}
              </button>
            )}
          </div>
        ),
      };

      setMessages((prev) => [...prev, aiMessage]);
      scrollToBottom();
    }, 1000);
  };

  const getPlaceholder = () => {
    if (!isOnboarding) return "What's on your mind?";

    switch (currentStep) {
      case "name":
        return "Enter your name...";
      case "wake_time":
        return "e.g., 7:00 AM";
      case "sleep_time":
        return "e.g., 11:00 PM";
      case "work_schedule":
        return "e.g., 9am-5pm or 'no'";
      case "chronotype":
        return "Morning person or night owl?";
      case "locations":
        return "Home and work locations...";
      case "existing_commitments":
        return "Any regular commitments?";
      default:
        return "What's on your mind?";
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
    <div className="relative h-screen flex flex-col overflow-hidden">
      <AmbientBackground variant="dark" />

      <div className="flex-1 overflow-y-auto px-4 pt-6 space-y-4 pb-4">
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
        disabled={isThinking || (isOnboarding && currentStep === "complete")}
        placeholder={getPlaceholder()}
      />

      <BottomNav />
    </div>
  );
}
