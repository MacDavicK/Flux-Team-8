import { AnimatePresence, motion } from "framer-motion";
import { useCallback, useEffect, useRef, useState } from "react";
import { ChatBubble } from "~/components/chat/ChatBubble";
import { MarkdownMessage } from "~/components/chat/MarkdownMessage";
import { OnboardingOptions } from "~/components/chat/OnboardingOptions";
import { ThinkingIndicator } from "~/components/chat/ThinkingIndicator";
import type { HistoryMessage } from "~/services/ChatService";
import { chatService } from "~/services/ChatService";
import type { ChatMessage, OnboardingOption } from "~/types";
import { MessageVariant } from "~/types/message";

const OTP_OPTIONS: OnboardingOption[] = [
  {
    label: "Enter verification code",
    value: null,
    zod_validator:
      'z.string().regex(/^\\d{6}$/, "Enter the 6-digit code from your SMS")',
    input_type: "otp",
  },
];

const PHONE_STEP_OPTIONS: OnboardingOption[] = [
  {
    label: "Specify",
    value: null,
    zod_validator:
      'z.string().regex(/^\\+[1-9]\\d{1,14}$/, "Enter your number in international format, e.g. +15551234567")',
    input_type: undefined,
  },
];

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
  const phoneStepOptionsRef = useRef<OnboardingOption[] | null>(null);

  const scrollToBottom = useCallback(() => {
    setTimeout(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, 50);
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [scrollToBottom]);

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
            setMessages([
              {
                id: "onboarding-0",
                type: MessageVariant.AI,
                content: message,
                options,
              },
            ]);
          }
        })
        .catch(() => {})
        .finally(() => setIsInitializing(false));

    chatService
      .getHistory()
      .then(({ messages: history, conversation_id }) => {
        if (conversation_id) conversationIdRef.current = conversation_id;

        const uiMessages: ChatMessage[] = history
          .filter(
            (m: HistoryMessage) => m.role === "user" || m.role === "assistant",
          )
          .map((m: HistoryMessage, i: number) => ({
            id: `history-${i}`,
            type: m.role === "user" ? MessageVariant.USER : MessageVariant.AI,
            content:
              m.role === "assistant" ? (
                <MarkdownMessage>{m.content}</MarkdownMessage>
              ) : (
                m.content
              ),
            // Restore options from persisted metadata (new messages).
            options:
              m.role === "assistant"
                ? (m.metadata?.options ?? undefined)
                : undefined,
          }));

        if (uiMessages.length > 0) {
          // For the last AI message, check whether we need to restore OTP state.
          // This covers both new messages (options in metadata) and old messages
          // (fallback: detect by question text and reattach static constants).
          const lastAssistant = [...history]
            .reverse()
            .find((m: HistoryMessage) => m.role === "assistant");
          const lastUiMsg = uiMessages[uiMessages.length - 1];
          const hasOtpOption = lastUiMsg?.options?.some(
            (o) => o.input_type === "otp",
          );

          // Fallback for old messages that predate metadata persistence.
          const isOtpStepByContent =
            !hasOtpOption &&
            (lastAssistant?.content?.includes("verification code") ?? false);

          if (isOtpStepByContent) {
            uiMessages[uiMessages.length - 1] = {
              ...uiMessages[uiMessages.length - 1],
              options: OTP_OPTIONS,
            };
          }

          // Restore phone number and phoneStepOptionsRef whenever we're at the OTP step.
          if (hasOtpOption || isOtpStepByContent) {
            const lastPhone = [...history]
              .reverse()
              .find(
                (m: HistoryMessage) =>
                  m.role === "user" &&
                  /^\+[1-9]\d{1,14}$/.test(m.content.trim()),
              );
            if (lastPhone) setOnboardingPhone(lastPhone.content.trim());
            phoneStepOptionsRef.current = PHONE_STEP_OPTIONS;
          }

          setMessages(uiMessages);
          setIsInitializing(false);
        } else {
          startFresh();
        }
      })
      .catch(() => startFresh());
  }, []);

  const handleChangeNumber = useCallback(() => {
    if (!phoneStepOptionsRef.current) return;
    const phoneOptions = phoneStepOptionsRef.current;
    setOnboardingPhone("");
    setMessages((prev) => {
      // Find the last AI message that has OTP options and replace its options
      // with the phone step options, effectively going back to phone input.
      const lastAiIdx = [...prev]
        .reverse()
        .findIndex(
          (m) =>
            m.type === MessageVariant.AI &&
            m.options &&
            m.options.some((o) => o.input_type === "otp"),
        );
      if (lastAiIdx === -1) return prev;
      const realIdx = prev.length - 1 - lastAiIdx;
      return prev.map((m, i) =>
        i === realIdx ? { ...m, options: phoneOptions } : m,
      );
    });
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
      const result = await chatService.sendMessage(
        text,
        conversationIdRef.current,
      );

      if (!conversationIdRef.current && result.conversation_id) {
        conversationIdRef.current = result.conversation_id;
      }

      setTimeout(() => {
        setIsThinking(false);

        // Cache phone step options when backend responds with the OTP step,
        // so "Change number" can restore them without a network round-trip.
        const isOtpStep = result.options?.some((o) => o.input_type === "otp");
        if (isOtpStep && phoneStepOptionsRef.current === null) {
          // The current message being processed was the phone number submission.
          // Find the phone step options from the last message's options.
          setMessages((prev) => {
            const last = [...prev]
              .reverse()
              .find((m) => m.options && m.options.length > 0);
            if (last?.options) phoneStepOptionsRef.current = last.options;
            return prev;
          });
        }

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
        content:
          "Sorry, I had trouble understanding that. Could you try again?",
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
              className={
                message.type === MessageVariant.USER ? "flex justify-end" : ""
              }
            >
              <ChatBubble variant={message.type} animate={false}>
                {message.content}
              </ChatBubble>
              {message.type === MessageVariant.AI &&
                message.options &&
                message.options.length > 0 && (
                  <OnboardingOptions
                    options={message.options}
                    onSelect={handleSendMessage}
                    onChangeNumber={handleChangeNumber}
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
