import { apiFetch } from "~/lib/apiClient";
import type { ChatMessageResponse, GoalClarifierAnswer } from "~/types";

const API_BASE =
  (import.meta as ImportMeta & { env?: { VITE_API_URL?: string } }).env
    ?.VITE_API_URL || "http://localhost:8002";
const DEMO_USER_ID = "a1000000-0000-0000-0000-000000000001";

export interface HistoryMessage {
  id: string;
  role: "user" | "assistant" | "system" | "summary";
  content: string;
  agent_node: string | null;
  created_at: string;
  metadata?: { proposed_plan?: Record<string, unknown> } | null;
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
    options?: { intent?: string; task_id?: string; answers?: GoalClarifierAnswer[] },
  ): Promise<ChatMessageResponse> {
    const response = await fetch(`${API_BASE}/orchestrator/message`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        conversation_id: conversationId ?? null,
        ...(options?.intent ? { intent: options.intent } : {}),
        ...(options?.task_id ? { task_id: options.task_id } : {}),
        ...(options?.answers ? { answers: options.answers } : {}),
      }),
    });

    if (!response.ok) {
      throw new Error("Failed to send chat message");
    }

    const data = (await response.json()) as {
      conversation_id?: string | null;
      message: string;
      route?: string;
      proposed_plan?: { [key: string]: unknown }[] | null;
      requires_user_action?: boolean;
      suggested_action?: string | null;
    };

    return {
      conversation_id: data.conversation_id ?? conversationId ?? "",
      message: data.message,
      agent_node: data.route ?? null,
      proposed_plan: data.proposed_plan ?? null,
      requires_user_action: Boolean(data.requires_user_action),
    };
  }
}

export const chatService = new ChatService();
