/**
 * Event domain types for Flux
 * @module types/event
 */

/**
 * Event type for visual theming
 */
export enum EventType {
  SAGE = "sage",
  TERRA = "terra",
  STONE = "stone",
}

/**
 * Event status in lifecycle
 */
export enum EventStatus {
  SCHEDULED = "SCHEDULED",
  IN_PROGRESS = "IN_PROGRESS",
  COMPLETED = "COMPLETED",
  CANCELLED = "CANCELLED",
}

/**
 * Timeline positioning for UI
 */
export interface TimelinePosition {
  top: number;
  height: number;
  left?: number;
  width?: number;
  zIndex?: number;
}

/**
 * Core event entity (meeting, appointment, etc.)
 */
export interface Event {
  /** Unique identifier */
  id: string;
  /** Event title */
  title: string;
  /** Detailed description */
  description?: string;
  /** Start time in ISO format */
  startTime: string;
  /** End time in ISO format */
  endTime: string;
  /** Visual type for theming */
  type: EventType;
  /** Current status */
  status: EventStatus;
  /** Associated attendees */
  attendees?: string[];
  /** Attendee avatar URLs */
  avatars?: string[];
  /** Location of event */
  location?: string;
  /** Whether event is recurring */
  isRecurring?: boolean;
  /** Recurrence rule */
  recurrenceRule?: string;
  /** Associated task IDs */
  taskIds?: string[];
  /** Calendar ID */
  calendarId?: string;
  /** Creation timestamp */
  createdAt?: string;
  /** Last update timestamp */
  updatedAt?: string;
}

/**
 * Event occurrence for recurring events
 */
export interface EventOccurrence {
  eventId: string;
  occurrenceDate: string;
  isException?: boolean;
  modifiedFields?: Partial<Event>;
}

/**
 * Timeline segment representing a time block
 */
export interface TimelineSegment {
  id: string;
  startTime: string;
  endTime: string;
  events: Event[];
  isEmpty?: boolean;
}
