import type { Goal } from '../types';
import apiClient from './client';
import { delay, mockGoals } from './mock';

const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true';

/**
 * Create a new goal from a user's natural-language message.
 * Optionally accepts additional context for the AI planner.
 * In mock mode, returns the pre-built "Wedding Weight Loss" plan.
 */
export async function createGoal(
  userMessage: string,
  context?: Record<string, unknown>,
): Promise<Goal> {
  if (USE_MOCK) {
    await delay();
    console.log('[MOCK] POST /api/goals/create', { userMessage, context });

    // Return the active mock goal as the "newly created" plan
    const activeGoal = mockGoals.find((g) => g.status === 'active');
    if (!activeGoal) throw { status: 500, message: 'No active mock goal found', url: '/api/goals/create' };
    return { ...activeGoal };
  }

  const response = await apiClient.post<Goal>('/api/goals/create', {
    message: userMessage,
    context,
  });
  return response.data;
}

/**
 * Fetch all goals for the current user.
 * In mock mode, returns both mock goals (completed + active).
 */
export async function getGoals(): Promise<Goal[]> {
  if (USE_MOCK) {
    await delay();
    console.log('[MOCK] GET /api/goals');
    return [...mockGoals];
  }

  const response = await apiClient.get<Goal[]>('/api/goals');
  return response.data;
}
