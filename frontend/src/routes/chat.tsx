import { createFileRoute } from "@tanstack/react-router";
import { AnimatePresence, motion } from "framer-motion";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { GoalPlannerAgent } from "~/agents/GoalPlannerAgent";
import { useSimulation } from "~/agents/SimulationContext";
import { ChatBubble } from "~/components/chat/ChatBubble";
import { ChatInput } from "~/components/chat/ChatInput";
import { PlanView } from "~/components/chat/PlanView";
import { ThinkingIndicator } from "~/components/chat/ThinkingIndicator";
import { BottomNav } from "~/components/navigation/BottomNav";
import { AmbientBackground } from "~/components/ui/AmbientBackground";

interface Message {
  id: string;
  type: "user" | "ai";
  content: React.ReactNode;
}

const initialMessages: Message[] = [
  {
    id: "1",
    type: "ai",
    content:
      "Hi! I'm here to help you break down your goals into manageable tasks. What would you like to achieve?",
  },
];

export const Route = createFileRoute("/chat")({
  component: ChatPage,
});

function ChatPage() {
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [isThinking, setIsThinking] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { locationAgent, stopEscalation } = useSimulation();

  // Initialize the GoalPlannerAgent
  const goalAgent = useMemo(() => new GoalPlannerAgent(), []);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [scrollToBottom]);

  const handleSendMessage = async (text: string) => {
    const userMessage: Message = {
      id: Date.now().toString(),
      type: "user",
      content: text,
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsThinking(true);

    // Stop any pending escalations if the user responds
    stopEscalation();

    // Decide which agent to use
    let response: any;
    const isLocationScenario =
      text.toLowerCase().includes("remind") ||
      locationAgent.getState() !== "IDLE";

    if (isLocationScenario) {
      response = await locationAgent.processMessage(text);
    }

    // Fallback to goal agent if location agent didn't handle it or it's not a location scenario
    if (!response || !response.message) {
      response = await goalAgent.processMessage(text);
    }

    setTimeout(() => {
      setIsThinking(false);

      if (!response) return;

      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        type: "ai",
        content: (
          <div className="space-y-3">
            <p>{response.message}</p>
            {response.type === "plan" && response.plan && (
              <PlanView
                plan={response.plan}
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
    }, 1000);
  };

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
              className={message.type === "user" ? "flex justify-end" : ""}
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
            <ChatBubble variant="ai" animate={false}>
              <ThinkingIndicator />
            </ChatBubble>
          </motion.div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <ChatInput onSend={handleSendMessage} disabled={isThinking} />

      <BottomNav />
    </div>
  );
}
