import type { Event } from '../types';
import apiClient from './client';
import { delay, mockEvents } from './mock';

const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true';

/**
 * Force an event to be marked as missed/drifted.
 * Useful for demoing the app's rescheduling behaviour.
 */
export async function forceMissTask(eventId: string): Promise<Event> {
  if (USE_MOCK) {
    await delay();
    console.log('[MOCK] POST /api/demo/force-miss', { eventId });

    const event = mockEvents.find((e) => e.id === eventId);
    if (!event)
      throw { status: 404, message: `Event ${eventId} not found`, url: '/api/demo/force-miss' };

    const updated: Event = { ...event, status: 'drifted' };

    // Mutate the mock array so subsequent calls reflect the change
    const idx = mockEvents.findIndex((e) => e.id === eventId);
    if (idx !== -1) mockEvents[idx] = updated;

    return updated;
  }

  const response = await apiClient.post<Event>('/api/demo/force-miss', {
    event_id: eventId,
  });
  return response.data;
}

/**
 * Fast-forward the simulated clock by a given number of hours.
 * Returns the new simulated current time as an ISO string.
 */
export async function timeWarp(
  hoursForward: number,
): Promise<{ new_current_time: string }> {
  if (USE_MOCK) {
    await delay();
    console.log('[MOCK] POST /api/demo/time-warp', { hoursForward });

    const now = new Date();
    now.setHours(now.getHours() + hoursForward);

    return { new_current_time: now.toISOString() };
  }

  const response = await apiClient.post<{ new_current_time: string }>('/api/demo/time-warp', {
    hours_forward: hoursForward,
  });
  return response.data;
}

/**
 * Reset the demo to its initial state.
 * Restores all mock data and resets the simulated clock.
 */
export async function resetDemo(): Promise<{ success: boolean }> {
  if (USE_MOCK) {
    await delay();
    console.log('[MOCK] POST /api/demo/reset');
    return { success: true };
  }

  const response = await apiClient.post<{ success: boolean }>('/api/demo/reset');
  return response.data;
}
