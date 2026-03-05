import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { AnimatePresence, motion } from "framer-motion";
import { History, MessageSquarePlus, X } from "lucide-react";
import React, { useCallback, useEffect, useRef, useState } from "react";
import { ChatBubble } from "~/components/chat/ChatBubble";
import { MarkdownMessage } from "~/components/chat/MarkdownMessage";
import { ChatInput } from "~/components/chat/ChatInput";
import { OnboardingOptions } from "~/components/chat/OnboardingOptions";
import { MilestoneRoadmapView, type RoadmapMilestone } from "~/components/chat/MilestoneRoadmapView";
import { PlanView } from "~/components/chat/PlanView";
import { TasksView, type ProposedTask } from "~/components/chat/TasksView";
import { ThinkingIndicator } from "~/components/chat/ThinkingIndicator";
import { BottomNav } from "~/components/navigation/BottomNav";
import { AmbientBackground } from "~/components/ui/AmbientBackground";
import { LoadingState } from "~/components/ui/LoadingState";
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

interface ParsedPlan {
  feasible: boolean;
  /** Present when feasible=true: tasks grouped by week for PlanView */
  milestones: PlanMilestone[] | null;
  /** Present when feasible=false: full milestone roadmap for MilestoneRoadmapView */
  roadmap: RoadmapMilestone[] | null;
  /** Present when feasible=false: proposed_tasks for the first milestone */
  firstMilestoneTasks: ProposedTask[] | null;
}

function parseProposedPlan(proposed_plan: Record<string, unknown>): ParsedPlan {
  const plan = proposed_plan.plan as Record<string, unknown> | undefined;
  const empty: ParsedPlan = { feasible: true, milestones: null, roadmap: null, firstMilestoneTasks: null };
  if (!plan) return empty;

  const feasible = plan.goal_feasible_in_6_weeks as boolean ?? true;

  // ── Multi-milestone path (goal not feasible in 6 weeks) ──────────────────
  if (!feasible) {
    const rawRoadmap = plan.milestone_roadmap as
      | Array<{ title: string; description?: string; pipeline_order?: number; target_weeks?: number }>
      | undefined;

    const roadmap: RoadmapMilestone[] | null =
      Array.isArray(rawRoadmap) && rawRoadmap.length > 0
        ? rawRoadmap
            .slice()
            .sort((a, b) => (a.pipeline_order ?? 0) - (b.pipeline_order ?? 0))
            .map((item) => ({
              title: item.title,
              description: item.description ?? "",
              pipeline_order: item.pipeline_order ?? 0,
              target_weeks: item.target_weeks ?? 6,
            }))
        : null;

    const rawTasks = plan.proposed_tasks as
      | Array<{
          title: string;
          description?: string;
          scheduled_days?: string[];
          suggested_time?: string;
          duration_minutes?: number;
          recurrence_rule?: string;
          week_range?: number[];
        }>
      | undefined;

    const firstMilestoneTasks: ProposedTask[] | null =
      Array.isArray(rawTasks) && rawTasks.length > 0
        ? rawTasks.map((t) => ({
            title: t.title,
            description: t.description ?? "",
            scheduled_days: t.scheduled_days ?? [],
            suggested_time: t.suggested_time ?? "",
            duration_minutes: t.duration_minutes ?? 30,
            recurrence_rule: t.recurrence_rule ?? "",
            week_range: t.week_range ?? [1, 6],
          }))
        : null;

    return { feasible: false, milestones: null, roadmap, firstMilestoneTasks };
  }

  // ── Single 6-week plan path ───────────────────────────────────────────────
  const rawTasks = plan.proposed_tasks as
    | Array<{ title: string; description?: string; week_range?: number[] }>
    | undefined;
  if (!Array.isArray(rawTasks) || rawTasks.length === 0) return empty;

  const groups = new Map<string, { weekStart: number; tasks: string[]; milestone: string }>();
  for (const task of rawTasks) {
    const [start = 1, end = start] = task.week_range ?? [1, 1];
    const key = start === end ? `${start}` : `${start}-${end}`;
    if (!groups.has(key)) {
      groups.set(key, { weekStart: start, tasks: [], milestone: task.description ?? "" });
    }
    groups.get(key)!.tasks.push(task.title);
  }

  const milestones: PlanMilestone[] = Array.from(groups.entries())
    .sort(([, a], [, b]) => a.weekStart - b.weekStart)
    .map(([key, { tasks: groupTasks, milestone }]) => ({
      week: key.includes("-") ? `Weeks ${key}` : `Week ${key}`,
      milestone,
      tasks: groupTasks,
    }));

  return { feasible: true, milestones, roadmap: null, firstMilestoneTasks: null };
}

function renderPlanUI(parsed: ParsedPlan, onConfirm: () => void): React.ReactNode {
  if (parsed.feasible && parsed.milestones) {
    return <PlanView plan={parsed.milestones} onConfirm={onConfirm} />;
  }
  if (!parsed.feasible) {
    return (
      <>
        {parsed.roadmap && <MilestoneRoadmapView milestones={parsed.roadmap} />}
        {parsed.firstMilestoneTasks && (
          <TasksView tasks={parsed.firstMilestoneTasks} onConfirm={onConfirm} />
        )}
      </>
    );
  }
  return null;
}

const WELCOME_MESSAGE = (name?: string) => {
  const firstName = name?.split(" ")[0];
  return `Hey${firstName ? ` ${firstName}` : ""}! 👋 I'm your **Flux** assistant.\n\nI can help you:\n- **Set and track goals** — break big ambitions into milestones\n- **Build habits** — create routines that stick\n- **Stay on top of tasks** — reminders, rescheduling, and follow-ups\n\nWhat would you like to work on today?`;
};

function ChatPage() {
  const navigate = useNavigate();
  const { isAuthenticated, isLoading: authLoading, user, patchUser } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isThinking, setIsThinking] = useState(false);
  const conversationIdRef = useRef<string | undefined>(undefined);
  const setConversationIdBoth = (id: string | undefined) => {
    conversationIdRef.current = id;
  };
  const [onboardingPhone, setOnboardingPhone] = useState("");
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [convCursor, setConvCursor] = useState<string | null>(null);
  const [convHasMore, setConvHasMore] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [isLoadingConversations, setIsLoadingConversations] = useState(false);
  const [isLoadingMoreConversations, setIsLoadingMoreConversations] = useState(false);
  const [isInitializing, setIsInitializing] = useState(false);
  const drawerScrollRef = useRef<HTMLDivElement | null>(null);

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
      setIsInitializing(true);
      chatService
        .getHistory()
        .then(({ messages: history, conversation_id }) => {
          if (conversation_id) setConversationIdBoth(conversation_id);

          const uiMessages: ChatMessage[] = history
            .filter((m: HistoryMessage) => m.role === "user" || m.role === "assistant")
            .map((m: HistoryMessage, i: number) => {
              const parsed =
                m.role === "assistant" && m.metadata?.proposed_plan
                  ? parseProposedPlan(m.metadata.proposed_plan)
                  : null;
              return {
                id: `history-${i}`,
                type: m.role === "user" ? MessageVariant.USER : MessageVariant.AI,
                content:
                  m.role === "assistant" ? (
                    <div className="space-y-3">
                      <MarkdownMessage>{m.content}</MarkdownMessage>
                      {parsed && renderPlanUI(parsed, () => handleSendMessage("Yes, this looks great!"))}
                    </div>
                  ) : (
                    m.content
                  ),
              };
            });

          if (uiMessages.length > 0) {
            setMessages(uiMessages);
            setIsInitializing(false);
          } else {
            // No prior messages — trigger backend to emit the first onboarding question
            chatService
              .startOnboarding()
              .then(({ conversation_id: cid, message, onboarding_options }) => {
                if (cid) setConversationIdBoth(cid);
                if (message) {
                  setMessages([{ id: "onboarding-0", type: MessageVariant.AI, content: message, onboardingOptions: onboarding_options }]);
                }
              })
              .catch(() => {})
              .finally(() => setIsInitializing(false));
          }
        })
        .catch(() => {
          // No prior history at all — trigger onboarding greeting
          chatService
            .startOnboarding()
            .then(({ conversation_id: cid, message, onboarding_options }) => {
              if (cid) setConversationIdBoth(cid);
              if (message) {
                setMessages([{ id: "onboarding-0", type: MessageVariant.AI, content: message, onboardingOptions: onboarding_options }]);
              }
            })
            .catch(() => {})
            .finally(() => setIsInitializing(false));
        });
    }
    // Onboarded: show a local welcome message. No server call needed —
    // the actual conversation is created on the first POST /chat/message.
    if (!isOnboarding) {
      setMessages([{
        id: "welcome",
        type: MessageVariant.AI,
        content: <MarkdownMessage>{WELCOME_MESSAGE(user?.name)}</MarkdownMessage>,
      }]);
    }
  }, [authLoading, isAuthenticated, isOnboarding, user?.name]);

  // Clear state and start a brand-new conversation.
  const startNewChat = useCallback(() => {
    initDoneRef.current = true;
    setMessages([{
      id: "welcome",
      type: MessageVariant.AI,
      content: <MarkdownMessage>{WELCOME_MESSAGE(user?.name)}</MarkdownMessage>,
    }]);
    setConversationIdBoth(undefined);
    setIsHistoryOpen(false);
    window.history.replaceState(null, "", "/chat");
  }, [user?.name]);

  // Load a specific past conversation from the history drawer.
  const loadConversation = useCallback(async (id: string) => {
    setIsHistoryOpen(false);
    setIsLoadingHistory(true);
    window.history.replaceState(null, "", `/chat?conversation=${id}`);
    try {
      const { messages: history, conversation_id } = await chatService.getHistory(id);
      if (conversation_id) setConversationIdBoth(conversation_id);

      const uiMessages: ChatMessage[] = history
        .filter((m: HistoryMessage) => m.role === "user" || m.role === "assistant")
        .map((m: HistoryMessage, i: number) => {
          const parsed =
            m.role === "assistant" && m.metadata?.proposed_plan
              ? parseProposedPlan(m.metadata.proposed_plan)
              : null;
          return {
            id: `history-${i}`,
            type: m.role === "user" ? MessageVariant.USER : MessageVariant.AI,
            content:
              m.role === "assistant" ? (
                <div className="space-y-3">
                  <MarkdownMessage>{m.content}</MarkdownMessage>
                  {parsed && renderPlanUI(parsed, () => handleSendMessage("Yes, this looks great!"))}
                </div>
              ) : (
                m.content
              ),
          };
        });

      setMessages(uiMessages);
    } catch {
      // Silently fail — keep current chat state.
    } finally {
      setIsLoadingHistory(false);
    }
  }, []);

  // Open history drawer and fetch the first page of conversations.
  const openHistory = useCallback(async () => {
    setIsHistoryOpen(true);
    setIsLoadingConversations(true);
    setConversations([]);
    setConvCursor(null);
    setConvHasMore(false);
    try {
      const page = await chatService.getConversations();
      setConversations(page.conversations);
      setConvCursor(page.next_cursor);
      setConvHasMore(page.has_more);
    } catch {
      setConversations([]);
    } finally {
      setIsLoadingConversations(false);
    }
  }, []);

  // Load the next page when the user scrolls to the bottom of the drawer.
  const loadMoreConversations = useCallback(async () => {
    if (!convHasMore || isLoadingMoreConversations) return;
    setIsLoadingMoreConversations(true);
    try {
      const page = await chatService.getConversations(convCursor ?? undefined);
      setConversations((prev) => [...prev, ...page.conversations]);
      setConvCursor(page.next_cursor);
      setConvHasMore(page.has_more);
    } catch {
      // keep existing list
    } finally {
      setIsLoadingMoreConversations(false);
    }
  }, [convHasMore, convCursor, isLoadingMoreConversations]);

  const handleSendMessage = async (text: string) => {
    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      type: MessageVariant.USER,
      content: text,
    };

    // Track phone number entered during onboarding so OTP widget can resend it
    if (isOnboarding && /^\+[1-9]\d{1,14}$/.test(text.trim())) {
      setOnboardingPhone(text.trim());
    }

    // Clear onboarding options from all previous messages when user sends a reply
    setMessages((prev) => [
      ...prev.map((m) => ({ ...m, onboardingOptions: null })),
      userMessage,
    ]);
    setIsThinking(true);
    scrollToBottom();
    stopEscalation();

    try {
      const result = await chatService.sendMessage(text, conversationIdRef.current);

      if (!conversationIdRef.current && result.conversation_id) {
        setConversationIdBoth(result.conversation_id);
        window.history.replaceState(null, "", `/chat?conversation=${result.conversation_id}`);
      }

      setTimeout(() => {
        setIsThinking(false);

        const parsed = result.proposed_plan
          ? parseProposedPlan(result.proposed_plan as Record<string, unknown>)
          : null;

        const aiMessage: ChatMessage = {
          id: (Date.now() + 1).toString(),
          type: MessageVariant.AI,
          content: (
            <div className="space-y-3">
              <MarkdownMessage>{result.message}</MarkdownMessage>
              {parsed
                ? renderPlanUI(parsed, () => handleSendMessage("Yes, this looks great!"))
                : result.requires_user_action
                  ? (
                    <button
                      type="button"
                      onClick={() => handleSendMessage("OK")}
                      className="text-sage font-medium text-sm hover:underline"
                    >
                      Confirm
                    </button>
                  )
                  : null}
            </div>
          ),
          onboardingOptions: result.onboarding_options,
        };

        setMessages((prev) => [...prev, aiMessage]);
        scrollToBottom();

        // Patch user.onboarded locally once the backend signals onboarding is
        // done (agent_node transitions away from "ONBOARDING"). This triggers
        // the redirect to "/" without an SSR round-trip or loading flash.
        if (isOnboarding && result.agent_node !== "ONBOARDING") {
          patchUser({ onboarded: true });
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
      <div className="relative min-h-screen flex flex-col items-center justify-center">
        <AmbientBackground variant="dark" />
        <LoadingState />
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
          {getGreeting(user?.name)}
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
          <div className="flex flex-col items-center justify-center h-full">
            <LoadingState />
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
                {message.type === MessageVariant.AI && message.onboardingOptions && message.onboardingOptions.length > 0 && (
                  <OnboardingOptions
                    options={message.onboardingOptions}
                    onSelect={handleSendMessage}
                    disabled={isThinking || isLoadingHistory || isInitializing}
                    phoneNumber={onboardingPhone}
                  />
                )}
              </motion.div>
            ))}
          </AnimatePresence>
        )}

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

      <ChatInput
        onSend={handleSendMessage}
        disabled={isThinking || isLoadingHistory || isInitializing}
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

              <div
                ref={drawerScrollRef}
                className="overflow-y-auto max-h-[55vh] pb-8"
                onScroll={(e) => {
                  const el = e.currentTarget;
                  if (el.scrollHeight - el.scrollTop - el.clientHeight < 80) {
                    loadMoreConversations();
                  }
                }}
              >
                {isLoadingConversations ? (
                  <div className="flex items-center justify-center py-8 gap-2">
                    {[0, 0.15, 0.3].map((delay, i) => (
                      <motion.div
                        key={i}
                        className="w-2 h-2 rounded-full bg-sage"
                        animate={{ scale: [1, 1.2, 1], opacity: [0.4, 1, 0.4] }}
                        transition={{ duration: 1.2, ease: "easeInOut", repeat: Infinity, delay }}
                      />
                    ))}
                  </div>
                ) : conversations.length === 0 ? (
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
                            {conv.title ?? conv.preview ?? "New conversation"}
                          </p>
                          <p className="text-river/60 text-xs mt-0.5">
                            {formatRelativeTime(conv.last_message_at ?? conv.created_at)}
                          </p>
                        </button>
                      </li>
                    ))}
                    {isLoadingMoreConversations && (
                      <li className="flex items-center justify-center py-4 gap-2">
                        {[0, 0.15, 0.3].map((delay, i) => (
                          <motion.div
                            key={i}
                            className="w-1.5 h-1.5 rounded-full bg-sage"
                            animate={{ scale: [1, 1.2, 1], opacity: [0.4, 1, 0.4] }}
                            transition={{ duration: 1.2, ease: "easeInOut", repeat: Infinity, delay }}
                          />
                        ))}
                      </li>
                    )}
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
