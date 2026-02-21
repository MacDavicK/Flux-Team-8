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
 * Sleep window configuration
 */
export interface SleepWindow {
  start: string;
  end: string;
}

/**
 * Work hours configuration
 */
export interface WorkHours {
  start: string;
  end: string;
  days: string[];
}

/**
 * Chronotype preference
 */
export type Chronotype = "morning" | "evening" | "neutral";

/**
 * Existing commitment (pre-seeded during onboarding)
 */
export interface ExistingCommitment {
  title: string;
  days: string[];
  time: string;
  duration_minutes: number;
}

/**
 * Location labels for GPS features
 */
export interface LocationLabels {
  home: string;
  work: string;
}

/**
 * Onboarding profile data collected during initial setup
 */
export interface OnboardingProfile {
  name: string;
  sleep_window: SleepWindow;
  work_hours: WorkHours;
  chronotype: Chronotype;
  existing_commitments: ExistingCommitment[];
  locations: LocationLabels;
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
  onboarded: boolean;
  onboardingProfile?: OnboardingProfile;
  createdAt?: string;
  lastActive?: string;
}

/**
 * Login request payload
 */
export interface LoginRequest {
  email: string;
  password: string;
}

/**
 * Login response
 */
export interface LoginResponse {
  user: User;
  token: string;
  success: boolean;
  message?: string;
}

/**
 * Signup request payload
 */
export interface SignupRequest {
  name: string;
  email: string;
  password: string;
}

/**
 * Signup response
 */
export interface SignupResponse {
  user: User;
  token: string;
  success: boolean;
  message?: string;
}

/**
 * Auth status response
 */
export interface AuthStatusResponse {
  isAuthenticated: boolean;
  user?: User;
  hasTasks?: boolean;
}

/**
 * Onboarding status response
 */
export interface OnboardingStatusResponse {
  onboarded: boolean;
  onboardingProfile?: OnboardingProfile;
}

/**
 * Onboarding chat message type
 */
export type OnboardingStep =
  | "name"
  | "wake_time"
  | "sleep_time"
  | "work_schedule"
  | "chronotype"
  | "locations"
  | "existing_commitments"
  | "first_goal"
  | "complete";

/**
 * Onboarding chat response
 */
export interface OnboardingChatResponse {
  message: string;
  nextStep: OnboardingStep;
  profile: Partial<OnboardingProfile>;
  isComplete: boolean;
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
