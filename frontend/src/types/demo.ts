/**
 * Demo mode types for Flux
 * @module types/demo
 */

import type { LucideIcon } from "lucide-react";

/**
 * Reschedule option from RescheduleModal
 */
export interface RescheduleOption {
  /** Option identifier */
  id: string;
  /** Display label */
  label: string;
  /** Associated icon */
  icon: LucideIcon;
  /** Color theme */
  color: "sage" | "terracotta" | "river" | "charcoal";
}

/**
 * Demo mode type
 */
export type DemoModeType = "time-warp" | "travel-mode" | "none";

/**
 * Time Warp simulation settings
 */
export interface TimeWarpSettings {
  /** Is time warp active */
  enabled: boolean;
  /** Speed multiplier */
  speed: number;
  /** Start time offset in hours */
  startOffset?: number;
  /** Current simulated time */
  simulatedTime?: string;
}

/**
 * Travel Mode simulation settings
 */
export interface TravelModeSettings {
  /** Is travel mode active */
  enabled: boolean;
  /** Current location */
  currentLocation?: {
    latitude: number;
    longitude: number;
    name: string;
  };
  /** Simulated movement path */
  path?: Array<{
    latitude: number;
    longitude: number;
    timestamp: string;
  }>;
  /** Trigger simulations enabled */
  triggersEnabled: boolean;
}

/**
 * Demo panel state
 */
export interface DemoPanelState {
  /** Is panel open */
  isOpen: boolean;
  /** Current demo mode */
  mode: DemoModeType;
  /** Time warp configuration */
  timeWarp: TimeWarpSettings;
  /** Travel mode configuration */
  travelMode: TravelModeSettings;
  /** Escalation speed multiplier */
  escalationSpeed: number;
  /** Selected trigger for simulation */
  selectedTrigger?: "leaving-home" | "near-store";
}

/**
 * Demo toggle state
 */
export interface DemoToggleState {
  id: string;
  label: string;
  isActive: boolean;
  icon?: LucideIcon;
  onToggle: () => void;
}

/**
 * Simulation event
 */
export interface SimulationEvent {
  id: string;
  type: "location" | "time" | "notification" | "escalation";
  timestamp: string;
  data: Record<string, unknown>;
  processed: boolean;
}
