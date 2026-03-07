import { AnimatePresence, motion } from "framer-motion";
import { useCallback, useEffect, useRef, useState } from "react";
import { ChatBubble } from "~/components/chat/ChatBubble";
import { MarkdownMessage } from "~/components/chat/MarkdownMessage";
import { OnboardingOptions } from "~/components/chat/OnboardingOptions";
import { ThinkingIndicator } from "~/components/chat/ThinkingIndicator";
import { chatService } from "~/services/ChatService";
import type { HistoryMessage } from "~/services/ChatService";
import type { ChatMessage } from "~/types";
import { MessageVariant } from "~/types/message";

interface OnboardingChatProps {
  onComplete: () => void;
}

export function OnboardingChat({ onComplete }: OnboardingChatProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isThinking, setIsThinking] = useState(false);
  const [isInitializing, setIsInitializing] = useState(true);
  const [onboardingPhone, setOnboardingPhone] = useState("");
  const [onboardingComplete, setOnboardingComplete] = useState(false);
  const conversationIdRef = useRef<string | undefined>(undefined);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const initDoneRef = useRef(false);

  const scrollToBottom = useCallback(() => {
    setTimeout(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, 50);
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // Initialise: resume last conversation or start fresh onboarding
  useEffect(() => {
    if (initDoneRef.current) return;
    initDoneRef.current = true;

    setIsInitializing(true);

    const startFresh = () =>
      chatService
        .startOnboarding()
        .then(({ conversation_id: cid, message, options }) => {
          if (cid) conversationIdRef.current = cid;
          if (message) {
            setMessages([{ id: "onboarding-0", type: MessageVariant.AI, content: message, options }]);
          }
        })
        .catch(() => {})
        .finally(() => setIsInitializing(false));

    chatService
      .getHistory()
      .then(({ messages: history, conversation_id }) => {
        if (conversation_id) conversationIdRef.current = conversation_id;

        const uiMessages: ChatMessage[] = history
          .filter((m: HistoryMessage) => m.role === "user" || m.role === "assistant")
          .map((m: HistoryMessage, i: number) => ({
            id: `history-${i}`,
            type: m.role === "user" ? MessageVariant.USER : MessageVariant.AI,
            content:
              m.role === "assistant" ? (
                <MarkdownMessage>{m.content}</MarkdownMessage>
              ) : (
                m.content
              ),
          }));

        if (uiMessages.length > 0) {
          setMessages(uiMessages);
          setIsInitializing(false);
        } else {
          startFresh();
        }
      })
      .catch(() => startFresh());
  }, []);

  const handleSendMessage = async (text: string) => {
    if (/^\+[1-9]\d{1,14}$/.test(text.trim())) {
      setOnboardingPhone(text.trim());
    }

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      type: MessageVariant.USER,
      content: /^\d{4}-\d{2}-\d{2}T/.test(text)
        ? (() => {
            try {
              return new Intl.DateTimeFormat(undefined, {
                weekday: "short",
                month: "short",
                day: "numeric",
                hour: "numeric",
                minute: "2-digit",
              }).format(new Date(text));
            } catch {
              return text;
            }
          })()
        : text,
    };

    setMessages((prev) => [
      ...prev.map((m) => ({ ...m, options: null })),
      userMessage,
    ]);
    setIsThinking(true);
    scrollToBottom();

    try {
      const result = await chatService.sendMessage(text, conversationIdRef.current);

      if (!conversationIdRef.current && result.conversation_id) {
        conversationIdRef.current = result.conversation_id;
      }

      setTimeout(() => {
        setIsThinking(false);

        const aiMessage: ChatMessage = {
          id: (Date.now() + 1).toString(),
          type: MessageVariant.AI,
          content: <MarkdownMessage>{result.message}</MarkdownMessage>,
          options: result.options,
        };

        setMessages((prev) => [...prev, aiMessage]);
        scrollToBottom();

        if (result.agent_node !== "ONBOARDING") {
          setOnboardingComplete(true);
        }
      }, 800);
    } catch {
      setIsThinking(false);
      const errorMessage: ChatMessage = {
        id: (Date.now() + 1).toString(),
        type: MessageVariant.AI,
        content: "Sorry, I had trouble understanding that. Could you try again?",
      };
      setMessages((prev) => [...prev, errorMessage]);
    }
  };

  return (
    <>
      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 pt-2 space-y-4 pb-4">
        <AnimatePresence mode="popLayout">
          {messages.map((message, index) => (
            <motion.div
              key={message.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ delay: index * 0.05 }}
              className={message.type === MessageVariant.USER ? "flex justify-end" : ""}
            >
              <ChatBubble variant={message.type} animate={false}>
                {message.content}
              </ChatBubble>
              {message.type === MessageVariant.AI && message.options && message.options.length > 0 && (
                <OnboardingOptions
                  options={message.options}
                  onSelect={handleSendMessage}
                  disabled={isThinking || isInitializing}
                  phoneNumber={onboardingPhone}
                />
              )}
            </motion.div>
          ))}
        </AnimatePresence>

        {(isThinking || isInitializing) && (
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

      {/* Bottom: CTA only when complete */}
      {onboardingComplete && (
        <div className="px-4 pb-8 pt-2 relative z-10">
          <motion.button
            type="button"
            onClick={onComplete}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            className="w-full py-3.5 rounded-2xl bg-sage text-white font-medium text-sm tracking-wide shadow-lg hover:bg-sage/90 active:scale-95 transition-transform"
          >
            Set my first goal →
          </motion.button>
        </div>
      )}
    </>
  );
}
