/**
 * Goal domain types for Flux
 * @module types/goal
 */

/**
 * Goal context for planning conversations
 */
export interface GoalContext {
  /** The goal description */
  goal?: string;
  /** Timeline for achievement */
  timeline?: string;
  /** Starting point/metric */
  currentStatus?: string;
  /** Target metric */
  targetStatus?: string;
  /** User preferences for approach */
  preferences?: string;
  /** Additional metadata */
  metadata?: Record<string, unknown>;
}

/**
 * Plan milestone structure
 */
export interface PlanMilestone {
  /** Week or time period */
  week: string;
  /** Milestone description */
  milestone: string;
  /** Tasks to complete */
  tasks: string[];
}

/**
 * Agent response from goal planner
 */
export interface AgentResponse {
  /** Message content */
  message: string;
  /** Response type */
  type: "text" | "plan";
  /** Plan milestones if type is 'plan' */
  plan?: PlanMilestone[];
  /** Suggested user action */
  suggestedAction?: string;
}

/**
 * Agent state in goal planning conversation
 */
export enum AgentState {
  /** Initial state */
  IDLE = "IDLE",
  /** Collecting timeline */
  GATHERING_TIMELINE = "GATHERING_TIMELINE",
  /** Collecting current metric */
  GATHERING_CURRENT_STATUS = "GATHERING_CURRENT_STATUS",
  /** Collecting target metric */
  GATHERING_TARGET_STATUS = "GATHERING_TARGET_STATUS",
  /** Collecting preferences */
  GATHERING_PREFERENCES = "GATHERING_PREFERENCES",
  /** Plan is ready for review */
  PLAN_READY = "PLAN_READY",
  /** Plan confirmed by user */
  CONFIRMED = "CONFIRMED",
}

/**
 * Goal status lifecycle
 */
export enum GoalStatus {
  /** Draft goal not yet started */
  DRAFT = "DRAFT",
  /** Active goal in progress */
  ACTIVE = "ACTIVE",
  /** Goal completed */
  COMPLETED = "COMPLETED",
  /** Goal abandoned */
  ABANDONED = "ABANDONED",
}

/**
 * Core goal entity
 */
export interface Goal {
  /** Unique identifier */
  id: string;
  /** User ID */
  userId: string;
  /** Goal title/description */
  title: string;
  /** Detailed description */
  description?: string;
  /** Goal category */
  category?: "fitness" | "career" | "personal" | "health" | "learning";
  /** Current status */
  status: GoalStatus;
  /** Target completion date */
  targetDate?: string;
  /** Associated milestones */
  milestones?: PlanMilestone[];
  /** Current agent state */
  agentState: AgentState;
  /** Conversation context */
  context: GoalContext;
  /** Progress percentage (0-100) */
  progress?: number;
  /** Associated task IDs */
  taskIds?: string[];
  /** Creation timestamp */
  createdAt: string;
  /** Last update timestamp */
  updatedAt: string;
  /** Completion timestamp */
  completedAt?: string;
}

/**
 * Goal progress tracking
 */
export interface GoalProgress {
  goalId: string;
  date: string;
  progress: number;
  notes?: string;
  metrics?: Record<string, number | string>;
}
