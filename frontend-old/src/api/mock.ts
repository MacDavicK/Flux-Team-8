import type { Event, Goal, User } from '../types';

/**
 * Simulate network latency with a random delay between 400–800ms.
 * @param ms Optional fixed delay; defaults to random 400–800ms.
 */
export function delay(ms?: number): Promise<void> {
  const duration = ms ?? Math.floor(Math.random() * 401) + 400;
  return new Promise((resolve) => setTimeout(resolve, duration));
}

/** Returns an ISO 8601 string for today at the given HH:MM. */
function todayAt(time: string): string {
  const [h, m] = time.split(':').map(Number);
  const d = new Date();
  d.setHours(h, m, 0, 0);
  return d.toISOString();
}

// ---------------------------------------------------------------------------
// Mock Events — 5 realistic health/fitness events for today
// ---------------------------------------------------------------------------

export const mockEvents: Event[] = [
  {
    id: 'evt-001',
    title: 'Morning Gym Session',
    description: 'Upper body workout — chest and triceps',
    start_time: todayAt('06:30'),
    end_time: todayAt('07:30'),
    status: 'completed',
    priority: 'must_not_miss',
    recurring: true,
    goal_id: 'goal-002',
  },
  {
    id: 'evt-002',
    title: 'Meal Prep — Lunch',
    description: 'Grilled chicken, brown rice, steamed broccoli (500 cal)',
    start_time: todayAt('09:00'),
    end_time: todayAt('09:30'),
    status: 'scheduled',
    priority: 'important',
    recurring: true,
    goal_id: 'goal-002',
  },
  {
    id: 'evt-003',
    title: 'Walking Meeting',
    description: '30 min walk — take the call outdoors',
    start_time: todayAt('12:00'),
    end_time: todayAt('12:30'),
    status: 'scheduled',
    priority: 'standard',
    recurring: false,
  },
  {
    id: 'evt-004',
    title: 'Evening Jog',
    description: '5K easy pace in the park',
    start_time: todayAt('17:30'),
    end_time: todayAt('18:15'),
    status: 'scheduled',
    priority: 'important',
    recurring: true,
    goal_id: 'goal-002',
  },
  {
    id: 'evt-005',
    title: 'Sleep Routine — Wind Down',
    description: 'No screens, light stretching, journal',
    start_time: todayAt('21:30'),
    end_time: todayAt('22:00'),
    status: 'scheduled',
    priority: 'standard',
    recurring: true,
  },
];

// ---------------------------------------------------------------------------
// Mock Goals
// ---------------------------------------------------------------------------

export const mockGoals: Goal[] = [
  {
    id: 'goal-001',
    domain: 'health_fitness',
    title: 'Build Consistent Exercise Habit',
    timeline_weeks: 4,
    created_at: '2026-01-15T00:00:00.000Z',
    status: 'completed',
    milestones: [
      {
        week: 1,
        title: 'Establish morning routine',
        tasks: ['Set alarm for 6 AM', 'Lay out gym clothes the night before', '3 gym sessions'],
        completed: true,
      },
      {
        week: 2,
        title: 'Increase intensity',
        tasks: ['Add 10% weight on lifts', 'Track all meals', '4 gym sessions'],
        completed: true,
      },
      {
        week: 4,
        title: 'Full consistency',
        tasks: ['5 sessions per week', 'Hit protein target daily', 'Log progress photo'],
        completed: true,
      },
    ],
  },
  {
    id: 'goal-002',
    domain: 'health_fitness',
    title: 'Wedding Weight Loss',
    timeline_weeks: 6,
    created_at: '2026-02-01T00:00:00.000Z',
    status: 'active',
    milestones: [
      {
        week: 1,
        title: 'Baseline & meal plan setup',
        tasks: ['Weigh in', 'Set calorie target', 'Prep first week of meals'],
        completed: true,
      },
      {
        week: 3,
        title: 'Mid-point check',
        tasks: ['Reassess calorie target', 'Add cardio session', 'Progress photo'],
        completed: false,
      },
      {
        week: 6,
        title: 'Final push & taper',
        tasks: ['Peak week diet', 'Light activity only', 'Final weigh-in'],
        completed: false,
      },
    ],
  },
];

// ---------------------------------------------------------------------------
// Mock User
// ---------------------------------------------------------------------------

export const mockUser: User = {
  id: 'user-001',
  name: 'Demo User',
  email: 'demo@flux.app',
  avatar_url: undefined,
  created_at: '2026-01-15T00:00:00.000Z',
};
