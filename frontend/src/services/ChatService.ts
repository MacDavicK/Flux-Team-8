import { apiFetch } from "~/lib/apiClient";
import { getNodeLabel } from "~/lib/nodeLabels";
import type {
  ChatMessageResponse,
  GoalClarifierAnswer,
  GoalClarifierQuestion,
  OnboardingOption,
} from "~/types";

export interface HistoryMessage {
  id: string;
  role: "user" | "assistant" | "system" | "summary";
  content: string;
  agent_node: string | null;
  created_at: string;
  metadata?: {
    proposed_plan?: Record<string, unknown>;
    options?: OnboardingOption[];
    questions?: GoalClarifierQuestion[];
    rag_used?: boolean;
    rag_sources?: { title: string; url: string | null }[];
    answers?: GoalClarifierAnswer[];
  } | null;
}

export interface ConversationSummary {
  id: string;
  last_message_at: string | null;
  created_at: string;
  title: string | null;
  preview: string | null;
}

export interface ConversationListPage {
  conversations: ConversationSummary[];
  has_more: boolean;
  next_cursor: string | null;
}

class ChatService {
  async getHistory(
    conversationId?: string,
    limit = 50,
  ): Promise<{ messages: HistoryMessage[]; conversation_id: string | null }> {
    const params = new URLSearchParams({ limit: String(limit) });
    if (conversationId) params.set("conversation_id", conversationId);
    const response = await apiFetch(`/api/v1/chat/history?${params}`);

    if (!response.ok) {
      throw new Error("Failed to fetch chat history");
    }

    return response.json();
  }

  async getConversations(cursor?: string): Promise<ConversationListPage> {
    const params = new URLSearchParams();
    if (cursor) params.set("cursor", cursor);
    const response = await apiFetch(`/api/v1/chat/conversations?${params}`);
    if (!response.ok) {
      throw new Error("Failed to fetch conversations");
    }
    return response.json() as Promise<ConversationListPage>;
  }

  async startOnboarding(): Promise<ChatMessageResponse> {
    const timezone = Intl.DateTimeFormat().resolvedOptions().timeZone;
    const response = await apiFetch("/api/v1/chat/onboarding/start", {
      method: "POST",
      body: JSON.stringify({ timezone }),
    });
    if (!response.ok && response.status !== 409) {
      throw new Error("Failed to start onboarding");
    }
    return response.json();
  }

  async resendOtp(phoneNumber: string): Promise<void> {
    const response = await apiFetch("/api/v1/account/phone/verify/send", {
      method: "POST",
      body: JSON.stringify({ phone_number: phoneNumber }),
    });
    if (!response.ok) {
      throw new Error("Failed to resend verification code");
    }
  }

  async sendMessage(
    message: string,
    conversationId?: string,
    options?: {
      intent?: string;
      task_id?: string;
      reschedule_scope?: string;
      answers?: GoalClarifierAnswer[];
    },
    onProgress?: (label: string) => void,
  ): Promise<ChatMessageResponse> {
    const response = await apiFetch("/api/v1/chat/message", {
      method: "POST",
      body: JSON.stringify({
        message,
        conversation_id: conversationId ?? null,
        ...(options?.intent ? { intent: options.intent } : {}),
        ...(options?.task_id ? { task_id: options.task_id } : {}),
        ...(options?.reschedule_scope
          ? { reschedule_scope: options.reschedule_scope }
          : {}),
        ...(options?.answers ? { answers: options.answers } : {}),
      }),
    });

    if (!response.ok) {
      throw new Error("Failed to send chat message");
    }

    // Parse SSE stream
    const reader = response.body?.getReader();
    if (!reader) throw new Error("Response body is null");
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      // Keep incomplete last line in buffer
      buffer = lines.pop() ?? "";

      for (const line of lines) {
        if (!line.startsWith("data: ")) continue;
        const raw = line.slice(6).trim();
        if (!raw) continue;

        let event: {
          type: string;
          node?: string;
          data?: unknown;
          message?: string;
        };
        try {
          event = JSON.parse(raw);
        } catch {
          continue;
        }

        if (event.type === "progress" && event.node && onProgress) {
          onProgress(getNodeLabel(event.node));
        } else if (event.type === "complete") {
          return event.data as ChatMessageResponse;
        } else if (event.type === "error") {
          throw new Error(event.message ?? "Stream error");
        }
      }
    }

    throw new Error("Stream ended without a complete event");
  }
}

export const chatService = new ChatService();
