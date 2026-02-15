export interface User {
  id: string;
  name: string;
  email: string;
  avatar_url?: string;
  created_at: string;
}

export interface Event {
  id: string;
  title: string;
  description?: string;
  start_time: string; // ISO 8601
  end_time: string;
  status: 'scheduled' | 'drifted' | 'completed' | 'missed';
  priority: 'standard' | 'important' | 'must_not_miss';
  recurring: boolean;
  goal_id?: string;
}

export interface Goal {
  id: string;
  domain: 'health_fitness' | 'career' | 'personal';
  title: string;
  timeline_weeks: number;
  created_at: string;
  status: 'active' | 'completed' | 'paused';
  milestones: Milestone[];
}

export interface Milestone {
  week: number;
  title: string;
  tasks: string[];
  completed: boolean;
}

export interface DemoState {
  enabled: boolean;
  timeWarpHours: number;
  currentSimulatedTime: string;
  panelOpen: boolean;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
}
