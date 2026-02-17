import { createFileRoute } from "@tanstack/react-router";
import { AnimatePresence, motion } from "framer-motion";
import { useCallback, useEffect, useRef, useState } from "react";
import { useSimulation } from "~/agents/SimulationContext";
import { ChatBubble } from "~/components/chat/ChatBubble";
import { ChatInput } from "~/components/chat/ChatInput";
import { PlanView } from "~/components/chat/PlanView";
import { ThinkingIndicator } from "~/components/chat/ThinkingIndicator";
import { BottomNav } from "~/components/navigation/BottomNav";
import { AmbientBackground } from "~/components/ui/AmbientBackground";
import { goalPlannerService } from "~/services/GoalPlannerService";
import type { ChatMessage, GoalContext, PlanMilestone } from "~/types";
import { AgentState } from "~/types/goal";
import { MessageVariant } from "~/types/message";

const initialMessages: ChatMessage[] = [
  {
    id: "1",
    type: MessageVariant.AI,
    content:
      "Hi! I'm here to help you break down your goals into manageable tasks. What would you like to achieve?",
  },
];

export const Route = createFileRoute("/chat")({
  component: ChatPage,
});

function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const [isThinking, setIsThinking] = useState(false);
  const [agentState, setAgentState] = useState<AgentState>(AgentState.IDLE);
  const [goalContext, setGoalContext] = useState<GoalContext>({});

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { stopEscalation } = useSimulation();

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [scrollToBottom]);

  const handleSendMessage = async (text: string) => {
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      type: MessageVariant.USER,
      content: text,
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsThinking(true);

    // Stop any pending escalations if the user responds
    stopEscalation();

    // Use goal planner service for all messages (backend handles routing)
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

      <ChatInput onSend={handleSendMessage} disabled={isThinking} />

      <BottomNav />
    </div>
  );
}
