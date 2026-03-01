import { apiFetch } from "~/lib/apiClient";
import type { ChatMessageResponse } from "~/types";

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
    const response = await apiFetch("/api/v1/chat/message", {
      method: "POST",
      body: JSON.stringify({
        message,
        conversation_id: conversationId ?? null,
      }),
    });

    if (!response.ok) {
      throw new Error("Failed to send chat message");
    }

    return response.json();
  }
}

export const chatService = new ChatService();
