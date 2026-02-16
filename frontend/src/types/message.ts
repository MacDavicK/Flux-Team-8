/**
 * Message domain types for Flux chat
 * @module types/message
 */

/**
 * Message sender variant
 */
export enum MessageVariant {
  USER = "user",
  AI = "ai",
}

/**
 * Content type for message classification
 */
export enum ContentType {
  TEXT = "TEXT",
  PLAN = "PLAN",
  TASK_SUGGESTION = "TASK_SUGGESTION",
  NOTIFICATION = "NOTIFICATION",
  WHATSAPP = "WHATSAPP",
  CALL = "CALL",
}

/**
 * Base message interface
 */
export interface BaseMessage {
  /** Unique identifier */
  id: string;
  /** Sender variant */
  type: MessageVariant;
  /** When message was sent */
  timestamp: string;
  /** Session ID */
  sessionId?: string;
}

/**
 * Text message content
 */
export interface TextMessage extends BaseMessage {
  contentType: ContentType.TEXT;
  text: string;
}

/**
 * Plan message with milestone structure
 */
export interface PlanMessage extends BaseMessage {
  contentType: ContentType.PLAN;
  text: string;
  plan: PlanMilestone[];
  suggestedAction?: string;
}

/**
 * Task suggestion message
 */
export interface TaskSuggestionMessage extends BaseMessage {
  contentType: ContentType.TASK_SUGGESTION;
  text: string;
  suggestions: TaskSuggestion[];
}

/**
 * Notification message
 */
export interface NotificationMessage extends BaseMessage {
  contentType: ContentType.NOTIFICATION;
  text: string;
  title?: string;
  actionUrl?: string;
  metadata?: Record<string, unknown>;
}

/**
 * WhatsApp message
 */
export interface WhatsAppMessage extends BaseMessage {
  contentType: ContentType.WHATSAPP;
  text: string;
  phoneNumber?: string;
}

/**
 * Call message
 */
export interface CallMessage extends BaseMessage {
  contentType: ContentType.CALL;
  text: string;
  duration?: number;
  recordingUrl?: string;
}

/**
 * Union type for all message content types
 */
export type MessageContent =
  | TextMessage
  | PlanMessage
  | TaskSuggestionMessage
  | NotificationMessage
  | WhatsAppMessage
  | CallMessage;

/**
 * Chat session for conversation management
 */
export interface ChatSession {
  /** Unique identifier */
  id: string;
  /** User ID */
  userId: string;
  /** Session title/topic */
  title?: string;
  /** Associated goal ID if any */
  goalId?: string;
  /** Session context/state */
  context?: GoalContext;
  /** Messages in session */
  messages: MessageContent[];
  /** Session status */
  status: "active" | "archived" | "closed";
  /** When session started */
  startedAt: string;
  /** When session ended */
  endedAt?: string;
  /** Last activity timestamp */
  lastActivityAt: string;
}

// Forward declarations to avoid circular dependencies
type PlanMilestone = {
  week: string;
  milestone: string;
  tasks: string[];
};

type GoalContext = {
  goal?: string;
  timeline?: string;
  currentWeight?: string;
  targetWeight?: string;
  preferences?: string;
  metadata?: Record<string, unknown>;
};

type TaskSuggestion = {
  title: string;
  duration?: string;
  category?: "WORK" | "PERSONAL" | "HEALTH";
  priority?: "LOW" | "MEDIUM" | "HIGH" | "URGENT";
};
