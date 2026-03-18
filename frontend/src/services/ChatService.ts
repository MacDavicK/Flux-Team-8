import { apiFetch } from "~/lib/apiClient";
import type { ChatMessageResponse } from "~/types";

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
}

export interface ConversationSummary {
  id: string;
  last_message_at: string | null;
  created_at: string;
  preview: string | null;
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

  async getConversations(limit = 20): Promise<ConversationSummary[]> {
    const response = await apiFetch(
      `/api/v1/chat/conversations?limit=${limit}`,
    );
    if (!response.ok) {
      throw new Error("Failed to fetch conversations");
    }
    const data = (await response.json()) as {
      conversations: ConversationSummary[];
    };
    return data.conversations;
  }

  async sendMessage(
    message: string,
    conversationId?: string,
  ): Promise<ChatMessageResponse> {
    const response = await fetch(`${API_BASE}/orchestrator/message`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        conversation_id: conversationId ?? null,
        user_id: DEMO_USER_ID,
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
