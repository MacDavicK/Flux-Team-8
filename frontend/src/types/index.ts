/**
 * Central type exports for Flux
 * @module types
 */

// Analytics domain
export type {
  EnergyPoint,
  FocusCategory,
  FocusMetrics,
  MetricTrend,
  ProductivityMetrics,
  WeeklyAnalytics,
} from "./analytics";
export {
  EnergyLevel,
  TrendDirection,
} from "./analytics";
// Common utilities
export type {
  AnimationConfig,
  ApiResponse,
  AsyncState,
  GlassEffect,
  ID,
  LoadingState,
  Nullable,
  PaginatedResponse,
  SortConfig,
  Timestamp,
  WithRequired,
} from "./common";
export {
  AnimationPresets,
  ColorTheme,
  SortDirection,
} from "./common";
// Demo domain
export type {
  DemoModeType,
  DemoPanelState,
  DemoToggleState,
  RescheduleOption,
  SimulationEvent,
  TimeWarpSettings,
  TravelModeSettings,
} from "./demo";
// Event domain
export type {
  Event,
  EventOccurrence,
  TimelineEvent,
  TimelinePosition,
  TimelineSegment,
} from "./event";
export {
  EventStatus,
  EventType,
} from "./event";
// Goal domain
export type {
  AgentResponse,
  Goal,
  GoalContext,
  GoalProgress,
  PlanMilestone,
} from "./goal";
export {
  AgentState,
  GoalStatus,
} from "./goal";
// Message domain
export type {
  BaseMessage,
  CallMessage,
  ChatMessage,
  ChatMessageRequest,
  ChatMessageResponse,
  ChatSession,
  MessageContent,
  NotificationMessage,
  PlanMessage,
  TaskSuggestionMessage,
  TextMessage,
  WhatsAppMessage,
} from "./message";
export {
  ContentType,
  MessageVariant,
} from "./message";
// Notification domain
export type {
  EscalationRule,
  Notification,
  NotificationAgentResponse,
  NotificationPreferences,
} from "./notification";
export {
  EscalationLevel,
  LocationReminderState,
  NotificationTrigger,
} from "./notification";
// Task domain
export type {
  RescheduleRequest,
  Task,
  TaskFilter,
  TaskRailItem,
  TaskSuggestion,
} from "./task";
export {
  Priority,
  TaskCategory,
  TaskStatus,
} from "./task";
// User domain
export type {
  AccountMe,
  AccountPatchRequest,
  AuthStatusResponse,
  Chronotype,
  ExistingCommitment,
  LocationLabels,
  LoginRequest,
  LoginResponse,
  OnboardingProfile,
  Preference,
  Profile,
  SignupRequest,
  SignupResponse,
  SleepWindow,
  User,
  WorkHours,
} from "./user";
export { ColorTheme as UserColorTheme } from "./user";
