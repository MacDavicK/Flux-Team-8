import { createFileRoute, redirect, useRouter } from "@tanstack/react-router";
import { AnimatePresence, motion } from "framer-motion";
import { History, MessageSquarePlus, X } from "lucide-react";
import type React from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import { z } from "zod";
import { ChatBubble } from "~/components/chat/ChatBubble";
import { ChatInput } from "~/components/chat/ChatInput";
import { GoalClarifierView } from "~/components/chat/GoalClarifierView";
import { MarkdownMessage } from "~/components/chat/MarkdownMessage";
import {
  MilestoneRoadmapView,
  type RoadmapMilestone,
} from "~/components/chat/MilestoneRoadmapView";
import { OnboardingOptions } from "~/components/chat/OnboardingOptions";
import { PlanView } from "~/components/chat/PlanView";
import { StartDatePicker } from "~/components/chat/StartDatePicker";
import { type ProposedTask, TasksView } from "~/components/chat/TasksView";
import { ThinkingIndicator } from "~/components/chat/ThinkingIndicator";
import { BottomNav } from "~/components/navigation/BottomNav";
import { AmbientBackground } from "~/components/ui/AmbientBackground";
import { LoadingState } from "~/components/ui/LoadingState";
import { useAuth } from "~/contexts/AuthContext";
import { useVoice } from "~/hooks/useVoice";
import { setInMemoryToken } from "~/lib/apiClient";
import { serverGetMe } from "~/lib/authServerFns";
import type { ConversationSummary } from "~/services/ChatService";
import { chatService } from "~/services/ChatService";
import { tasksService } from "~/services/TasksService";
import type { ChatMessage, PlanMilestone } from "~/types";
import { MessageVariant } from "~/types/message";

const _MAX_CHAT_RETRIES = 2;

/** Substring that indicates the "no expert guidance" fallback message (show in plan card banner). */
const _FALLBACK_EXPERT_PREFIX =
  "I don't have expert guidance for this specific goal yet";
const _RETRY_DELAY_MS = 1500;

export const Route = createFileRoute("/chat")({
  pendingComponent: () => (
    <div className="relative min-h-screen flex flex-col items-center justify-center">
      <AmbientBackground variant="dark" />
      <LoadingState />
    </div>
  ),
  pendingMs: 0,
  validateSearch: z.object({
    reschedule_task_id: z.string().optional(),
    task_name: z.string().optional(),
    conversation: z.string().optional(),
  }),
  loader: async () => {
    const { user, token } = await serverGetMe();
    if (!user) throw redirect({ to: "/login" });
    if (!user.onboarded) throw redirect({ to: "/onboarding" });
    return { user, token };
  },
  component: ChatPage,
});

function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffDays = Math.floor(
    (now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24),
  );
  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays} days ago`;
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function getGreeting(name?: string): string {
  const hour = new Date().getHours();
  const salutation =
    hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";
  return name ? `${salutation}, ${name.split(" ")[0]}` : salutation;
}

interface ParsedPlan {
  feasible: boolean;
  milestones: PlanMilestone[] | null;
  roadmap: RoadmapMilestone[] | null;
  firstMilestoneTasks: ProposedTask[] | null;
}

function parseProposedPlan(proposed_plan: Record<string, unknown>): ParsedPlan {
  const plan = proposed_plan.plan as Record<string, unknown> | undefined;
  const empty: ParsedPlan = {
    feasible: true,
    milestones: null,
    roadmap: null,
    firstMilestoneTasks: null,
  };
  if (!plan) return empty;

  const feasible = (plan.goal_feasible_in_6_weeks as boolean) ?? true;

  if (!feasible) {
    const rawRoadmap = plan.milestone_roadmap as
      | Array<{
          title: string;
          description?: string;
          pipeline_order?: number;
          target_weeks?: number;
        }>
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

  const rawTasks = plan.proposed_tasks as
    | Array<{ title: string; description?: string; week_range?: number[] }>
    | undefined;
  if (!Array.isArray(rawTasks) || rawTasks.length === 0) return empty;

  const groups = new Map<
    string,
    { weekStart: number; tasks: string[]; milestone: string }
  >();
  for (const task of rawTasks) {
    const [start = 1, end = start] = task.week_range ?? [1, 1];
    const key = start === end ? `${start}` : `${start}-${end}`;
    if (!groups.has(key)) {
      groups.set(key, {
        weekStart: start,
        tasks: [],
        milestone: task.description ?? "",
      });
    }
    groups.get(key)?.tasks.push(task.title);
  }

  const milestones: PlanMilestone[] = Array.from(groups.entries())
    .sort(([, a], [, b]) => a.weekStart - b.weekStart)
    .map(([key, { tasks: groupTasks, milestone }]) => ({
      week: key.includes("-") ? `Weeks ${key}` : `Week ${key}`,
      milestone,
      tasks: groupTasks,
    }));

  return {
    feasible: true,
    milestones,
    roadmap: null,
    firstMilestoneTasks: null,
  };
}

function renderPlanUI(
  parsed: ParsedPlan,
  onConfirm: () => void,
): React.ReactNode {
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

function formatSlotLabel(iso: string): string {
  try {
    return new Intl.DateTimeFormat(undefined, {
      weekday: "short",
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

const WELCOME_MESSAGE = (name?: string) => {
  const firstName = name?.split(" ")[0];
  return `Hey${firstName ? ` ${firstName}` : ""}! 👋 I'm your **Flux** assistant.\n\nI can help you:\n- **Set and track goals** — break big ambitions into milestones\n- **Build habits** — create routines that stick\n- **Stay on top of tasks** — reminders, rescheduling, and follow-ups\n\nWhat would you like to work on today?`;
};

function ChatPage() {
  const router = useRouter();
  const { user, refreshAuthStatus } = useAuth();
  const { token } = Route.useLoaderData();
  useEffect(() => {
    setInMemoryToken(token);
  }, [token]);
  const { reschedule_task_id, task_name, conversation } = Route.useSearch();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isThinking, setIsThinking] = useState(false);
  const [progressLabel, setProgressLabel] = useState<string | undefined>(
    undefined,
  );
  const conversationIdRef = useRef<string | undefined>(undefined);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [convCursor, setConvCursor] = useState<string | null>(null);
  const [convHasMore, setConvHasMore] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [isLoadingConversations, setIsLoadingConversations] = useState(false);
  const [isLoadingMoreConversations, setIsLoadingMoreConversations] =
    useState(false);
  const [activeClarifier, setActiveClarifier] = useState<{
    questions: import("~/types").GoalClarifierQuestion[];
    messageId: string;
  } | null>(null);
  const drawerScrollRef = useRef<HTMLDivElement | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const initDoneRef = useRef(false);
  // Preserve reschedule_task_id across URL rewrites (it's cleared from search params
  // when conversation_id is substituted in, but we still need it for slot confirmation).
  const rescheduleTaskIdRef = useRef<string | undefined>(reschedule_task_id);
  const lastInputWasVoiceRef = useRef<boolean>(false);
  const voice = useVoice();

  const scrollToBottom = useCallback(() => {
    setTimeout(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, 50);
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [scrollToBottom]);

  // On mount: if reschedule_task_id is present, auto-submit the reschedule request.
  // Otherwise show the standard welcome message.
  useEffect(() => {
    if (initDoneRef.current) return;
    initDoneRef.current = true;

    if (reschedule_task_id) {
      const displayName = task_name ?? "this task";
      const userMsg: ChatMessage = {
        id: "reschedule-user",
        type: MessageVariant.USER,
        content: `Help me reschedule "${displayName}"`,
      };
      setMessages([userMsg]);
      setIsThinking(true);

      chatService
        .sendMessage(`Help me reschedule "${displayName}"`, undefined, {
          intent: "RESCHEDULE_TASK",
          task_id: reschedule_task_id,
        })
        .then((result) => {
          setIsThinking(false);
          if (result.conversation_id) {
            conversationIdRef.current = result.conversation_id;
            window.history.replaceState(
              null,
              "",
              `/chat?conversation=${result.conversation_id}`,
            );
          } else {
            window.history.replaceState(null, "", "/chat");
          }
          const aiMsg: ChatMessage = {
            id: "reschedule-ai",
            type: MessageVariant.AI,
            content: <MarkdownMessage>{result.message}</MarkdownMessage>,
            options: result.options,
          };
          setMessages((prev) => [...prev, aiMsg]);
          scrollToBottom();
        })
        .catch(() => {
          setIsThinking(false);
          setProgressLabel(undefined);
          window.history.replaceState(null, "", "/chat");
          setMessages((prev) => [
            ...prev,
            {
              id: "reschedule-error",
              type: MessageVariant.AI,
              content:
                "Sorry, I couldn't load reschedule options. Please try again.",
            },
          ]);
        });
      return;
    }

    setMessages([
      {
        id: "welcome",
        type: MessageVariant.AI,
        content: (
          <MarkdownMessage>{WELCOME_MESSAGE(user?.name)}</MarkdownMessage>
        ),
      },
    ]);
  }, [user?.name, reschedule_task_id, task_name, scrollToBottom]);

  const startNewChat = useCallback(() => {
    initDoneRef.current = true;
    setMessages([
      {
        id: "welcome",
        type: MessageVariant.AI,
        content: (
          <MarkdownMessage>{WELCOME_MESSAGE(user?.name)}</MarkdownMessage>
        ),
      },
    ]);
    conversationIdRef.current = undefined;
    setIsHistoryOpen(false);
    window.history.replaceState(null, "", "/chat");
  }, [user?.name]);

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

  const handleSendMessage = useCallback(
    async (text: string) => {
      // Handle slot confirmation (ISO UTC string from reschedule options)
      if (rescheduleTaskIdRef.current && /^\d{4}-\d{2}-\d{2}T/.test(text)) {
        const slotLabel = formatSlotLabel(text);
        setMessages((prev) => [
          ...prev.map((m) => ({ ...m, options: null })),
          {
            id: Date.now().toString(),
            type: MessageVariant.USER,
            content: slotLabel,
          },
        ]);
        setIsThinking(true);
        tasksService
          .confirmReschedule(rescheduleTaskIdRef.current, text)
          .then(() => {
            setIsThinking(false);
            setProgressLabel(undefined);
            // Invalidate router cache so the home page re-fetches updated tasks.
            router.invalidate();
            setMessages((prev) => [
              ...prev,
              {
                id: Date.now().toString(),
                type: MessageVariant.AI,
                content: (
                  <MarkdownMessage>
                    Done! Your task has been rescheduled. You'll get a reminder
                    at the new time.
                  </MarkdownMessage>
                ),
              },
            ]);
            scrollToBottom();
          })
          .catch(() => {
            setIsThinking(false);
            setMessages((prev) => [
              ...prev,
              {
                id: Date.now().toString(),
                type: MessageVariant.AI,
                content:
                  "Sorry, I couldn't confirm that reschedule. Please try again.",
              },
            ]);
          });
        return;
      }

      const userMessage: ChatMessage = {
        id: Date.now().toString(),
        type: MessageVariant.USER,
        content: /^\d{4}-\d{2}-\d{2}T/.test(text)
          ? formatSlotLabel(text)
          : text,
      };

      // Clear options from all previous messages when the user responds
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
          undefined,
          (label) => setProgressLabel(label),
        );

        if (!conversationIdRef.current && result.conversation_id) {
          conversationIdRef.current = result.conversation_id;
          window.history.replaceState(
            null,
            "",
            `/chat?conversation=${result.conversation_id}`,
          );
        }

        setTimeout(() => {
          setIsThinking(false);
          setProgressLabel(undefined);

          const parsed = result.proposed_plan
            ? parseProposedPlan(result.proposed_plan as Record<string, unknown>)
            : null;

          const isStartDatePrompt = result.agent_node === "ask_start_date";

          const msgId = (Date.now() + 1).toString();
          const aiMessage: ChatMessage = {
            id: msgId,
            type: MessageVariant.AI,
            content: (
              <div className="space-y-3">
                <MarkdownMessage>{result.message}</MarkdownMessage>
                {isStartDatePrompt ? (
                  <StartDatePicker
                    onSelect={(date) => handleSendMessage(date)}
                  />
                ) : parsed ? (
                  renderPlanUI(parsed, () =>
                    handleSendMessage("Yes, this looks great!"),
                  )
                ) : result.requires_user_action && !result.options?.length ? (
                  <button
                    type="button"
                    onClick={() => handleSendMessage("OK")}
                    className="text-sage font-medium text-sm hover:underline"
                  >
                    Confirm
                  </button>
                ) : null}
              </div>
            ),
            options: result.options,
          };

          setMessages((prev) => [...prev, aiMessage]);

          // Refresh auth state so hasTasks flips when backend has persisted tasks.
          refreshAuthStatus();

          if (result.questions?.length) {
            setActiveClarifier({
              questions: result.questions,
              messageId: msgId,
            });
          }

          if (lastInputWasVoiceRef.current && result.spoken_summary) {
            lastInputWasVoiceRef.current = false;
            voice.playTTS(result.spoken_summary);
          }

          scrollToBottom();
        }, 800);
      } catch {
        setIsThinking(false);
        setProgressLabel(undefined);
        const errorMessage: ChatMessage = {
          id: (Date.now() + 1).toString(),
          type: MessageVariant.AI,
          content:
            "Sorry, I had trouble understanding that. Could you try again?",
        };
        setMessages((prev) => [...prev, errorMessage]);
      }
    },
    [scrollToBottom, router, voice, refreshAuthStatus],
  );

  const loadConversation = useCallback(
    async (id: string) => {
      setIsHistoryOpen(false);
      setIsLoadingHistory(true);
      window.history.replaceState(null, "", `/chat?conversation=${id}`);
      try {
        const { messages: history, conversation_id } =
          await chatService.getHistory(id);
        if (conversation_id) conversationIdRef.current = conversation_id;

        const filtered = history.filter(
          (m) => m.role === "user" || m.role === "assistant",
        );
        // Only the last assistant message can still be awaiting a start date
        const lastAssistantIdx = filtered.reduce(
          (acc, m, i) => (m.role === "assistant" ? i : acc),
          -1,
        );
        const uiMessages: ChatMessage[] = filtered.map((m, i) => {
          const parsed =
            m.role === "assistant" && m.metadata?.proposed_plan
              ? parseProposedPlan(m.metadata.proposed_plan)
              : null;
          const isStartDatePrompt =
            m.role === "assistant" &&
            m.agent_node === "ask_start_date" &&
            i === lastAssistantIdx;
          return {
            id: `history-${i}`,
            type: m.role === "user" ? MessageVariant.USER : MessageVariant.AI,
            content:
              m.role === "assistant" ? (
                <div className="space-y-3">
                  <MarkdownMessage>{m.content}</MarkdownMessage>
                  {isStartDatePrompt ? (
                    <StartDatePicker
                      onSelect={(date) => handleSendMessage(date)}
                    />
                  ) : (
                    parsed &&
                    renderPlanUI(parsed, () =>
                      handleSendMessage("Yes, this looks great!"),
                    )
                  )}
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
    },
    [handleSendMessage],
  );

  // If conversation_id is in the URL (e.g. page reload), load that conversation.
  // Intentionally depends only on `token` — runs once after token is hydrated,
  // not on every loadConversation identity change.
  // biome-ignore lint/correctness/useExhaustiveDependencies: intentional one-shot on token hydration
  useEffect(() => {
    if (!conversation || !token) return;
    loadConversation(conversation);
  }, [token]);

  return (
    <div className="relative h-screen flex flex-col overflow-hidden">
      <AmbientBackground variant="dark" />

      {/* Header */}
      <div className="flex items-center justify-between px-5 pt-12 pb-3 relative z-10">
        <h1 className="font-display italic text-xl text-charcoal/80">
          {getGreeting(user?.name)}
        </h1>
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
                      disabled={isThinking}
                    />
                  )}
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
              <ThinkingIndicator label={progressLabel} />
            </ChatBubble>
          </motion.div>
        )}

        <div ref={messagesEndRef} />
      </div>

      <ChatInput
        onSend={handleSendMessage}
        onVoiceSend={() => {
          lastInputWasVoiceRef.current = true;
        }}
        disabled={isThinking || isLoadingHistory}
        placeholder={
          messages.length <= 1
            ? "What would you like to achieve?"
            : "What's on your mind?"
        }
        voice={voice}
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
                <h2 className="font-display italic text-lg text-charcoal">
                  Past Chats
                </h2>
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
                    {[0, 0.15, 0.3].map((delay) => (
                      <motion.div
                        key={delay}
                        className="w-2 h-2 rounded-full bg-sage"
                        animate={{ scale: [1, 1.2, 1], opacity: [0.4, 1, 0.4] }}
                        transition={{
                          duration: 1.2,
                          ease: "easeInOut",
                          repeat: Infinity,
                          delay,
                        }}
                      />
                    ))}
                  </div>
                ) : conversations.length === 0 ? (
                  <p className="text-center text-river/60 text-sm py-8">
                    No past conversations yet.
                  </p>
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
                            {formatRelativeTime(
                              conv.last_message_at ?? conv.created_at,
                            )}
                          </p>
                        </button>
                      </li>
                    ))}
                    {isLoadingMoreConversations && (
                      <li className="flex items-center justify-center py-4 gap-2">
                        {[0, 0.15, 0.3].map((delay) => (
                          <motion.div
                            key={delay}
                            className="w-1.5 h-1.5 rounded-full bg-sage"
                            animate={{
                              scale: [1, 1.2, 1],
                              opacity: [0.4, 1, 0.4],
                            }}
                            transition={{
                              duration: 1.2,
                              ease: "easeInOut",
                              repeat: Infinity,
                              delay,
                            }}
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

      {/* Goal Clarifier Sheet */}
      <AnimatePresence>
        {activeClarifier && (
          <GoalClarifierView
            questions={activeClarifier.questions}
            disabled={isThinking}
            onDismiss={() => setActiveClarifier(null)}
            onSubmit={(answers) => {
              setActiveClarifier(null);
              const summary = answers
                .map((a) => `${a.question}: ${a.answer}`)
                .join(", ");
              setMessages((prev) => [
                ...prev,
                {
                  id: Date.now().toString(),
                  type: MessageVariant.USER,
                  content: summary,
                },
              ]);
              setIsThinking(true);
              scrollToBottom();
              chatService
                .sendMessage(
                  summary,
                  conversationIdRef.current,
                  { intent: "GOAL_CLARIFY", answers },
                  (label) => setProgressLabel(label),
                )
                .then((result) => {
                  if (!conversationIdRef.current && result.conversation_id) {
                    conversationIdRef.current = result.conversation_id;
                    window.history.replaceState(
                      null,
                      "",
                      `/chat?conversation=${result.conversation_id}`,
                    );
                  }
                  setTimeout(() => {
                    setIsThinking(false);
                    setProgressLabel(undefined);
                    const parsed = result.proposed_plan
                      ? parseProposedPlan(
                          result.proposed_plan as Record<string, unknown>,
                        )
                      : null;
                    const isStartDatePrompt =
                      result.agent_node === "ask_start_date";
                    setMessages((prev) => [
                      ...prev,
                      {
                        id: (Date.now() + 1).toString(),
                        type: MessageVariant.AI,
                        content: (
                          <div className="space-y-3">
                            <MarkdownMessage>{result.message}</MarkdownMessage>
                            {isStartDatePrompt ? (
                              <StartDatePicker
                                onSelect={(date) => handleSendMessage(date)}
                              />
                            ) : parsed ? (
                              renderPlanUI(parsed, () =>
                                handleSendMessage("Yes, this looks great!"),
                              )
                            ) : null}
                          </div>
                        ),
                        options: result.options,
                      },
                    ]);
                    scrollToBottom();
                  }, 800);
                })
                .catch(() => {
                  setIsThinking(false);
                  setProgressLabel(undefined);
                  setMessages((prev) => [
                    ...prev,
                    {
                      id: Date.now().toString(),
                      type: MessageVariant.AI,
                      content:
                        "Sorry, I had trouble understanding that. Could you try again?",
                    },
                  ]);
                });
            }}
          />
        )}
      </AnimatePresence>
    </div>
  );
}
