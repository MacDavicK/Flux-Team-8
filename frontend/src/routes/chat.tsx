import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { AnimatePresence, motion } from "framer-motion";
import { History, MessageSquarePlus, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { ChatBubble } from "~/components/chat/ChatBubble";
import { ChatInput } from "~/components/chat/ChatInput";
import { PlanView } from "~/components/chat/PlanView";
import { ThinkingIndicator } from "~/components/chat/ThinkingIndicator";
import { BottomNav } from "~/components/navigation/BottomNav";
import { AmbientBackground } from "~/components/ui/AmbientBackground";
import { useAuth } from "~/contexts/AuthContext";
import { useSimulation } from "~/contexts/SimulationContext";
import { chatService } from "~/services/ChatService";
import type { ConversationSummary, HistoryMessage } from "~/services/ChatService";
import type { ChatMessage, PlanMilestone } from "~/types";
import { MessageVariant } from "~/types/message";

export const Route = createFileRoute("/chat")({
  component: ChatPage,
});

function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));
  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays} days ago`;
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function getGreeting(name?: string): string {
  const hour = new Date().getHours();
  const salutation = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";
  return name ? `${salutation}, ${name.split(" ")[0]}` : salutation;
}

function ChatPage() {
  const navigate = useNavigate();
  const { isAuthenticated, isLoading: authLoading, user, refreshAuthStatus } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isThinking, setIsThinking] = useState(false);
  const [conversationId, setConversationId] = useState<string | undefined>(undefined);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const { stopEscalation } = useSimulation();
  const initDoneRef = useRef(false);

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

  // Navigate to home once onboarding completes (user.onboarded flips to true).
  // Only redirect if the user arrived at /chat because they were non-onboarded;
  // once onboarding finishes send them to the flow page.
  const wasOnboardingRef = useRef(false);
  useEffect(() => {
    if (isOnboarding) wasOnboardingRef.current = true;
  }, [isOnboarding]);
  useEffect(() => {
    if (!authLoading && isAuthenticated && user?.onboarded && wasOnboardingRef.current) {
      navigate({ to: "/" });
    }
  }, [authLoading, isAuthenticated, user?.onboarded, navigate]);

  // Initialise chat once auth is ready.
  // Onboarding: resume the most recent conversation so the user picks up where
  // they left off. The agent drives the questions — no hardcoded greeting.
  // Onboarded: always start fresh. History is accessible via the History drawer.
  useEffect(() => {
    if (authLoading || !isAuthenticated || initDoneRef.current) return;
    initDoneRef.current = true;

    if (isOnboarding) {
      chatService
        .getHistory()
        .then(({ messages: history, conversation_id }) => {
          if (conversation_id) setConversationId(conversation_id);

          const uiMessages: ChatMessage[] = history
            .filter((m: HistoryMessage) => m.role === "user" || m.role === "assistant")
            .map((m: HistoryMessage, i: number) => ({
              id: `history-${i}`,
              type: m.role === "user" ? MessageVariant.USER : MessageVariant.AI,
              content: m.content,
            }));

          setMessages(uiMessages);
        })
        .catch(() => {
          // No prior history — leave empty; agent responds on first send.
        });
    }
    // Onboarded: leave messages empty and conversationId undefined.
    // A new conversation is created server-side on the first POST /chat/message.
  }, [authLoading, isAuthenticated, isOnboarding]);

  // Clear state and start a brand-new conversation.
  const startNewChat = useCallback(() => {
    initDoneRef.current = true;
    setMessages([]);
    setConversationId(undefined);
    setIsHistoryOpen(false);
  }, []);

  // Load a specific past conversation from the history drawer.
  const loadConversation = useCallback(async (id: string) => {
    setIsHistoryOpen(false);
    setIsLoadingHistory(true);
    try {
      const { messages: history, conversation_id } = await chatService.getHistory(id);
      if (conversation_id) setConversationId(conversation_id);

      const uiMessages: ChatMessage[] = history
        .filter((m: HistoryMessage) => m.role === "user" || m.role === "assistant")
        .map((m: HistoryMessage, i: number) => ({
          id: `history-${i}`,
          type: m.role === "user" ? MessageVariant.USER : MessageVariant.AI,
          content: m.content,
        }));

      setMessages(uiMessages);
    } catch {
      // Silently fail — keep current chat state.
    } finally {
      setIsLoadingHistory(false);
    }
  }, []);

  // Open history drawer and fetch the conversations list.
  const openHistory = useCallback(async () => {
    setIsHistoryOpen(true);
    try {
      const list = await chatService.getConversations();
      setConversations(list);
    } catch {
      setConversations([]);
    }
  }, []);

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

    try {
      const result = await chatService.sendMessage(text, conversationId);

      if (!conversationId) {
        setConversationId(result.conversation_id);
      }


      setTimeout(() => {
        setIsThinking(false);

        const aiMessage: ChatMessage = {
          id: (Date.now() + 1).toString(),
          type: MessageVariant.AI,
          content: (
            <div className="space-y-3">
              <p>{result.message}</p>
              {result.proposed_plan && (
                <PlanView
                  plan={result.proposed_plan as unknown as PlanMilestone[]}
                  onConfirm={() => handleSendMessage("Yes, this looks great!")}
                />
              )}
              {result.requires_user_action && (
                <button
                  type="button"
                  onClick={() => handleSendMessage("OK")}
                  className="text-sage font-medium text-sm hover:underline"
                >
                  Confirm
                </button>
              )}
            </div>
          ),
        };

        setMessages((prev) => [...prev, aiMessage]);
        scrollToBottom();

        if (isOnboarding) {
          refreshAuthStatus().catch(() => {});
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

      {/* Header */}
      <div className="flex items-center justify-between px-5 pt-12 pb-3 relative z-10">
        <h1 className="font-display italic text-xl text-charcoal/80">
          {isOnboarding ? "Getting started" : getGreeting(user?.name)}
        </h1>
        {!isOnboarding && (
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={openHistory}
              aria-label="Chat history"
              className="w-9 h-9 flex items-center justify-center rounded-full glass-bubble text-river hover:text-charcoal transition-colors"
            >
              <History className="w-4 h-4" />
            </button>
            <button
              type="button"
              onClick={startNewChat}
              aria-label="New chat"
              className="w-9 h-9 flex items-center justify-center rounded-full glass-bubble text-river hover:text-charcoal transition-colors"
            >
              <MessageSquarePlus className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-4 pt-2 space-y-4 pb-4">
        {isLoadingHistory ? (
          <div className="flex items-center justify-center h-full">
            <div className="animate-pulse text-sage text-sm">Loading conversation…</div>
          </div>
        ) : (
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
              </motion.div>
            ))}
          </AnimatePresence>
        )}

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
        disabled={isThinking || isLoadingHistory}
        placeholder={messages.length === 0 ? "What would you like to achieve?" : "What's on your mind?"}
      />

      <BottomNav />

      {/* History Drawer */}
      <AnimatePresence>
        {isHistoryOpen && (
          <>
            <motion.div
              className="fixed inset-0 z-40 bg-black/30"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setIsHistoryOpen(false)}
            />

            <motion.div
              className="fixed bottom-0 left-0 right-0 z-50 max-w-md mx-auto rounded-t-2xl bg-white/90 backdrop-blur-xl border-t border-glass-border"
              initial={{ y: "100%" }}
              animate={{ y: 0 }}
              exit={{ y: "100%" }}
              transition={{ type: "spring", damping: 30, stiffness: 300 }}
            >
              <div className="flex items-center justify-between px-5 pt-5 pb-3">
                <h2 className="font-display italic text-lg text-charcoal">Past Chats</h2>
                <button
                  type="button"
                  onClick={() => setIsHistoryOpen(false)}
                  className="w-8 h-8 flex items-center justify-center rounded-full bg-black/5 text-river hover:text-charcoal transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="overflow-y-auto max-h-[55vh] pb-8">
                {conversations.length === 0 ? (
                  <p className="text-center text-river/60 text-sm py-8">No past conversations yet.</p>
                ) : (
                  <ul className="divide-y divide-glass-border">
                    {conversations.map((conv) => (
                      <li key={conv.id}>
                        <button
                          type="button"
                          onClick={() => loadConversation(conv.id)}
                          className="w-full text-left px-5 py-4 hover:bg-black/5 transition-colors"
                        >
                          <p className="text-charcoal text-sm font-medium line-clamp-1">
                            {conv.preview ?? "New conversation"}
                          </p>
                          <p className="text-river/60 text-xs mt-0.5">
                            {formatRelativeTime(conv.last_message_at ?? conv.created_at)}
                          </p>
                        </button>
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  );
}
