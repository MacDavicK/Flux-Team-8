/**
 * Common utility types shared across Flux
 * @module types/common
 */

/**
 * Color theme options for UI consistency
 */
export enum ColorTheme {
  SAGE = "sage",
  TERRACOTTA = "terracotta",
  RIVER = "river",
  STONE = "stone",
  CHARCOAL = "charcoal",
}

/**
 * Glass effect configuration for UI components
 */
export interface GlassEffect {
  /** Background opacity (0-1) */
  opacity: number;
  /** Blur amount in pixels */
  blur: number;
  /** Border opacity (0-1) */
  borderOpacity?: number;
  /** Background color tint */
  tint?: ColorTheme;
}

/**
 * Animation configuration for Framer Motion
 */
export interface AnimationConfig {
  /** Animation duration in seconds */
  duration?: number;
  /** Animation delay in seconds */
  delay?: number;
  /** Easing function */
  ease?: number[] | string;
  /** Spring stiffness */
  stiffness?: number;
  /** Spring damping */
  damping?: number;
  /** Spring mass */
  mass?: number;
}

/**
 * Standard Framer Motion transition presets
 */
export const AnimationPresets = {
  /** Quick fade */
  fade: { duration: 0.3, ease: "easeOut" },
  /** Spring bounce */
  spring: { type: "spring", stiffness: 300, damping: 30 },
  /** Smooth slide */
  slide: { duration: 0.4, ease: [0.34, 1.56, 0.64, 1] },
  /** Scale pop */
  pop: { duration: 0.2, ease: "easeInOut" },
} as const;

/**
 * Timestamp type alias
 */
export type Timestamp = string;

/**
 * ID type alias for entity identifiers
 */
export type ID = string;

/**
 * Nullable type helper
 */
export type Nullable<T> = T | null | undefined;

/**
 * Require at least one of the specified fields
 */
export type RequireAtLeastOne<T, Keys extends keyof T = keyof T> = Pick<
  T,
  Exclude<keyof T, Keys>
> &
  {
    [K in Keys]-?: Required<Pick<T, K>> & Partial<Pick<T, Exclude<Keys, K>>>;
  }[Keys];

/**
 * Make specific fields required
 */
export type WithRequired<T, K extends keyof T> = T & { [P in K]-?: T[P] };

/**
 * API response wrapper
 */
export interface ApiResponse<T> {
  data: T;
  success: boolean;
  message?: string;
  error?: string;
}

/**
 * Paginated response
 */
export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  pageSize: number;
  hasMore: boolean;
}

/**
 * Sort direction
 */
export enum SortDirection {
  ASC = "asc",
  DESC = "desc",
}

/**
 * Sort configuration
 */
export interface SortConfig<T = string> {
  field: T;
  direction: SortDirection;
}

/**
 * Loading state
 */
export interface LoadingState {
  isLoading: boolean;
  error: Error | null;
}

/**
 * Async operation state
 */
export interface AsyncState<T> extends LoadingState {
  data: T | null;
}
