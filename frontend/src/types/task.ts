/**
 * Task domain types for Flux
 * @module types/task
 */

/**
 * Task status lifecycle
 */
export enum TaskStatus {
  PENDING = "PENDING",
  IN_PROGRESS = "IN_PROGRESS",
  COMPLETED = "COMPLETED",
  OVERDUE = "OVERDUE",
  CANCELLED = "CANCELLED",
}

/**
 * Task priority levels
 */
export enum Priority {
  LOW = "LOW",
  MEDIUM = "MEDIUM",
  HIGH = "HIGH",
  URGENT = "URGENT",
}

/**
 * Task category for focus areas
 */
export enum TaskCategory {
  WORK = "WORK",
  PERSONAL = "PERSONAL",
  HEALTH = "HEALTH",
}

/**
 * Core task entity
 */
export interface Task {
  /** Unique identifier */
  id: string;
  /** Task title */
  title: string;
  /** Current status in lifecycle */
  status: TaskStatus;
  /** Detailed description */
  description?: string;
  /** Estimated duration (e.g., "30 min", "2 hours") */
  duration?: string;
  /** Priority level */
  priority?: Priority;
  /** Due date in ISO format */
  dueDate?: string;
  /** When the task was completed */
  completedAt?: string;
  /** Associated tags */
  tags?: string[];
  /** Category for focus tracking */
  category?: TaskCategory;
  /** User who created the task */
  userId?: string;
  /** Parent task for subtasks */
  parentId?: string;
  /** Subtasks */
  subtasks?: Task[];
  /** Creation timestamp */
  createdAt?: string;
  /** Last update timestamp */
  updatedAt?: string;
}

/**
 * Task suggestion from AI
 */
export interface TaskSuggestion {
  title: string;
  duration?: string;
  category?: TaskCategory;
  priority?: Priority;
}

/**
 * Task filter options
 */
export interface TaskFilter {
  status?: TaskStatus[];
  category?: TaskCategory[];
  priority?: Priority[];
  dueBefore?: string;
  dueAfter?: string;
  tags?: string[];
  searchQuery?: string;
}
