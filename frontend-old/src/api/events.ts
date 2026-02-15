import type { Event } from '../types';
import apiClient from './client';
import { delay, mockEvents } from './mock';

const USE_MOCK = import.meta.env.VITE_USE_MOCK === 'true';

/**
 * Fetch events, optionally filtered by date (YYYY-MM-DD).
 * In mock mode, returns predefined events for today.
 */
export async function getEvents(date?: string): Promise<Event[]> {
  if (USE_MOCK) {
    await delay();
    console.log('[MOCK] GET /api/events', { date });

    if (!date) return [...mockEvents];

    return mockEvents.filter((evt) => evt.start_time.startsWith(date));
  }

  const response = await apiClient.get<Event[]>('/api/events', {
    params: { date },
  });
  return response.data;
}

/**
 * Reschedule an event to a new start time with a reason.
 * Returns the updated event.
 */
export async function rescheduleEvent(
  id: string,
  newStartTime: string,
  reason: string,
): Promise<Event> {
  if (USE_MOCK) {
    await delay();
    console.log('[MOCK] POST /api/events/reschedule', { id, newStartTime, reason });

    const event = mockEvents.find((e) => e.id === id);
    if (!event) throw { status: 404, message: `Event ${id} not found`, url: `/api/events/${id}` };

    // Compute new end time by preserving original duration
    const originalStart = new Date(event.start_time).getTime();
    const originalEnd = new Date(event.end_time).getTime();
    const duration = originalEnd - originalStart;
    const newEnd = new Date(new Date(newStartTime).getTime() + duration).toISOString();

    const updated: Event = {
      ...event,
      start_time: newStartTime,
      end_time: newEnd,
      status: 'drifted',
    };

    // Mutate the mock array so subsequent calls reflect the change
    const idx = mockEvents.findIndex((e) => e.id === id);
    if (idx !== -1) mockEvents[idx] = updated;

    return updated;
  }

  const response = await apiClient.post<Event>(`/api/events/${id}/reschedule`, {
    new_start_time: newStartTime,
    reason,
  });
  return response.data;
}
