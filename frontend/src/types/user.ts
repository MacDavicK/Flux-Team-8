/**
 * User domain types for Flux
 * @module types/user
 */

/**
 * User preferences and settings
 */
export interface Preference {
  theme?: ColorTheme;
  notifications?: boolean;
  emailDigest?: "daily" | "weekly" | "none";
  timezone?: string;
  language?: string;
  weekStartsOn?: 0 | 1 | 2 | 3 | 4 | 5 | 6;
}

/**
 * User profile with extended settings
 */
export interface Profile {
  id: string;
  userId: string;
  bio?: string;
  location?: string;
  timezone: string;
  preferences: Preference;
  createdAt: string;
  updatedAt: string;
}

/**
 * Core user entity
 */
export interface User {
  id: string;
  name: string;
  email: string;
  avatar?: string;
  preferences?: Preference;
  profile?: Profile;
  createdAt?: string;
  lastActive?: string;
}

/**
 * Color theme options
 */
export enum ColorTheme {
  SAGE = "sage",
  TERRACOTTA = "terracotta",
  RIVER = "river",
  STONE = "stone",
  CHARCOAL = "charcoal",
}

/**
 * User profile API response
 */
export interface UserProfileResponse {
  id: string;
  name: string;
  email: string;
  avatar?: string;
}

/**
 * Weekly stats pill data
 */
export interface WeeklyStatsPill {
  icon: "check" | "clock" | "flame";
  value: string;
  label: string;
}

/**
 * User stats API response
 */
export interface UserStatsResponse {
  title: string;
  stats: WeeklyStatsPill[];
}

/**
 * User energy aura API response
 */
export interface UserEnergyAuraResponse {
  data: Array<{
    date: string;
    intensity: number;
  }>;
}

/**
 * User focus distribution API response
 */
export interface UserFocusDistributionResponse {
  work: number;
  personal: number;
  health: number;
}

/**
 * User weekly insight API response
 */
export interface UserWeeklyInsightResponse {
  title: string;
  insight: string;
}
