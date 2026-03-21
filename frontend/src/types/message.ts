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
  currentStatus?: string;
  targetStatus?: string;
  preferences?: string;
  metadata?: Record<string, unknown>;
};

type TaskSuggestion = {
  title: string;
  duration?: string;
  category?: "WORK" | "PERSONAL" | "HEALTH";
  priority?: "LOW" | "MEDIUM" | "HIGH" | "URGENT";
};

/**
 * A single answer to a clarifying question, submitted as part of GOAL_CLARIFY intent.
 */
export interface GoalClarifierAnswer {
  question_id: string; // matches GoalClarifierQuestion.id
  question: string; // original question text (for conversation history context)
  answer: string; // selected option or custom input
}

/**
 * A structured clarifying question returned by the backend when agent_node == "GOAL_CLARIFY".
 * The frontend presents these one-by-one locally, then submits all answers in one batch.
 */
export interface GoalClarifierQuestion {
  id: string;
  question: string;
  options: string[]; // pre-defined choices (empty = open-ended)
  allows_custom: boolean; // true if user can type a custom answer
  zod_validator: string | null; // Zod schema string for validating custom input
  required: boolean;
}

/**
 * Real backend: POST /api/v1/chat/message request body
 */
export interface ChatMessageRequest {
  message: string;
  conversation_id?: string | null;
  intent?: string | null; // "GOAL_CLARIFY" when submitting answers batch
  answers?: GoalClarifierAnswer[] | null; // structured answers for GOAL_CLARIFY
}

/**
 * A quick-select option shown during onboarding.
 * value=null means "Specify" — the frontend opens a validated text input.
 */
export interface OnboardingOption {
  label: string;
  value: string | null;
  zod_validator: string | null;
  input_type?: string | null; // "otp" renders the OTP verification widget
}

/**
 * Real backend: POST /api/v1/chat/message response
 *
 * options — OnboardingOption[] for onboarding/reschedule flows
 * questions — GoalClarifierQuestion[] when agent_node == "GOAL_CLARIFY"
 */
export interface ChatMessageResponse {
  conversation_id: string;
  message: string;
  agent_node?: string | null;
  proposed_plan?: Record<string, unknown> | null;
  requires_user_action: boolean;
  options?: OnboardingOption[] | null;
  questions?: GoalClarifierQuestion[] | null;
  spoken_summary?: string | null;
  rag_used: boolean;
  rag_sources: { title: string; url: string | null }[];
}

/**
 * UI-specific chat message for React components
 * Allows React.ReactNode content for rendering rich UI
 */
export interface ChatMessage {
  /** Unique identifier */
  id: string;
  /** Sender variant */
  type: MessageVariant;
  /** Content as React node for UI rendering */
  content: React.ReactNode;
  /** Quick-select options shown below this message */
  options?: OnboardingOption[] | null;
  /** Structured clarifying questions for GOAL_CLARIFY flow */
  questions?: GoalClarifierQuestion[] | null;
  /** RAG provenance metadata */
  provenance?: {
    rag_used: boolean;
    rag_sources: { title: string; url: string | null }[];
  };
}
