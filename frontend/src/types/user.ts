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
  token?: string;
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
  token?: string;
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
 * Real backend: GET /api/v1/account/me response
 */
export interface AccountMe {
  id: string;
  email?: string | null;
  name?: string | null;
  timezone?: string | null;
  onboarded?: boolean | null;
  phone_verified?: boolean | null;
  notification_preferences?: { [key: string]: unknown } | null;
  monthly_token_usage?: { [key: string]: unknown } | null;
}

/**
 * Real backend: PATCH /api/v1/account/me request body
 */
export interface AccountPatchRequest {
  timezone?: string | null;
  notification_preferences?: { [key: string]: unknown } | null;
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

