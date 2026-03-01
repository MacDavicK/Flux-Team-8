/**
 * Analytics domain types for Flux
 * @module types/analytics
 */

/**
 * Energy level classification
 */
export enum EnergyLevel {
  LOW = "LOW",
  MEDIUM = "MEDIUM",
  HIGH = "HIGH",
}

/**
 * Energy point for aura visualization
 */
export interface EnergyPoint {
  /** Date in ISO format */
  date: string;
  /** Intensity value 0-1 */
  intensity: number;
  /** Category of activity */
  category?: "work" | "personal" | "health" | "rest";
  /** Specific timestamp */
  timestamp?: string;
  /** Additional metadata */
  metadata?: {
    source?: string;
    activity?: string;
    notes?: string;
    [key: string]: unknown;
  };
}

/**
 * Focus category for distribution tracking
 */
export interface FocusCategory {
  /** Category name */
  name: string;
  /** Hours spent */
  value: number;
  /** Percentage of total */
  percent: number;
  /** Display color */
  color: string;
}

/**
 * Focus metrics with strict fields
 */
export interface FocusMetrics {
  /** Work hours */
  work: number;
  /** Personal hours */
  personal: number;
  /** Health hours */
  health: number;
  /** Total hours (computed) */
  total: number;
  /** Time period identifier */
  period: string;
  /** Period start date */
  periodStart?: string;
  /** Period end date */
  periodEnd?: string;
  /** Categories breakdown */
  categories?: FocusCategory[];
}

/**
 * Productivity metrics
 */
export interface ProductivityMetrics {
  /** Tasks completed */
  tasksCompleted: number;
  /** Tasks created */
  tasksCreated: number;
  /** Completion rate (0-1) */
  completionRate: number;
  /** Average task duration in minutes */
  averageTaskDuration?: number;
  /** Focus sessions count */
  focusSessions?: number;
  /** Total focus time in minutes */
  totalFocusTime?: number;
  /** Distraction count */
  distractions?: number;
}

/**
 * Weekly analytics summary
 */
export interface WeeklyAnalytics {
  userId: string;
  weekStart: string;
  weekEnd: string;
  /** Energy data points */
  energyData: EnergyPoint[];
  /** Focus distribution */
  focusMetrics: FocusMetrics;
  /** Productivity stats */
  productivity: ProductivityMetrics;
  /** Goals progress */
  goalsProgress: {
    goalId: string;
    progress: number;
    tasksCompleted: number;
    tasksTotal: number;
  }[];
  /** Generated insights */
  insights?: string[];
}

/**
 * Trend direction
 */
export enum TrendDirection {
  UP = "UP",
  DOWN = "DOWN",
  STABLE = "STABLE",
}

/**
 * Metric trend over time
 */
export interface MetricTrend {
  metric: string;
  currentValue: number;
  previousValue: number;
  change: number;
  changePercent: number;
  direction: TrendDirection;
  period: string;
}
