/**
 * Notification domain types for Flux
 * @module types/notification
 */

/**
 * Location reminder agent state
 */
export enum LocationReminderState {
  /** Initial state */
  IDLE = "IDLE",
  /** Waiting for location trigger */
  WAITING_FOR_TRIGGER = "WAITING_FOR_TRIGGER",
  /** User is near store */
  NEAR_STORE = "NEAR_STORE",
  /** Reminder snoozed */
  SNOOZED = "SNOOZED",
  /** Task completed */
  COMPLETED = "COMPLETED",
}

/**
 * Escalation level for notifications
 */
export enum EscalationLevel {
  /** Standard notification */
  NOTIFICATION = "NOTIFICATION",
  /** WhatsApp message */
  WHATSAPP = "WHATSAPP",
  /** Phone call */
  CALL = "CALL",
}

/**
 * Notification trigger type
 */
export enum NotificationTrigger {
  /** User leaving home */
  LEAVING_HOME = "leaving_home",
  /** User near grocery store */
  NEAR_GROCERY = "near_grocery",
}

/**
 * Extended agent response for location-based notifications
 * Also used as AgentResponse in LocationReminderAgent context
 */
export interface AgentResponse {
  /** Message content */
  message: string;
  /** Response type */
  type: "text" | "plan" | "notification" | "whatsapp" | "call";
  /** Distance to location if applicable */
  distance?: string;
  /** Trigger that activated this response */
  trigger?: NotificationTrigger;
  /** Plan data if type is 'plan' */
  plan?: unknown[];
  /** Suggested user action */
  suggestedAction?: string;
}

/**
 * Extended agent response alias for notification-specific contexts
 */
export type NotificationAgentResponse = AgentResponse;

/**
 * Core notification entity
 */
export interface Notification {
  /** Unique identifier */
  id: string;
  /** User ID */
  userId: string;
  /** Notification title */
  title: string;
  /** Notification body */
  body: string;
  /** Current escalation level */
  escalationLevel: EscalationLevel;
  /** Related task ID */
  taskId?: string;
  /** Related goal ID */
  goalId?: string;
  /** Trigger that caused this notification */
  trigger?: NotificationTrigger;
  /** Whether notification has been read */
  isRead: boolean;
  /** Whether notification has been acted upon */
  isActioned: boolean;
  /** Action taken by user */
  action?: "done" | "snooze" | "dismiss";
  /** Location data */
  location?: {
    latitude: number;
    longitude: number;
    accuracy?: number;
  };
  /** Creation timestamp */
  createdAt: string;
  /** When notification was read */
  readAt?: string;
  /** When notification was actioned */
  actionedAt?: string;
}

/**
 * Notification preferences
 */
export interface NotificationPreferences {
  userId: string;
  /** Enable push notifications */
  pushEnabled: boolean;
  /** Enable location-based reminders */
  locationEnabled: boolean;
  /** Enable WhatsApp escalation */
  whatsappEnabled: boolean;
  /** Enable call escalation */
  callEnabled: boolean;
  /** Quiet hours start */
  quietHoursStart?: string;
  /** Quiet hours end */
  quietHoursEnd?: string;
  /** Default escalation delay in minutes */
  escalationDelayMinutes: number;
}

/**
 * Escalation rule configuration
 */
export interface EscalationRule {
  id: string;
  userId: string;
  /** Escalation level */
  level: EscalationLevel;
  /** Delay before escalating (in minutes) */
  delayMinutes: number;
  /** Conditions for escalation */
  conditions?: {
    requireLocation?: boolean;
    requireTimeOfDay?: boolean;
    timeRange?: { start: string; end: string };
  };
  /** Is this rule active */
  isActive: boolean;
}
