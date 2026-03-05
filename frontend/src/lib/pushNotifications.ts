import { apiFetch } from '~/lib/apiClient';

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const rawData = window.atob(base64);
  return Uint8Array.from([...rawData].map((c) => c.charCodeAt(0)));
}

async function saveSubscriptionToBackend(sub: PushSubscription): Promise<void> {
  await apiFetch('/api/v1/account/push-subscription', {
    method: 'POST',
    body: JSON.stringify({ subscription: sub.toJSON() }),
  });
}

/**
 * Registers the service worker and subscribes to Web Push.
 * - If the user already has a subscription, re-saves it to backend (handles token rotation).
 * - Returns true if successfully subscribed, false if not supported or permission denied.
 */
export async function registerAndSubscribe(): Promise<boolean> {
  if (!('serviceWorker' in navigator) || !('PushManager' in window)) return false;

  const permission = Notification.permission;
  if (permission === 'denied') return false;

  const reg = await navigator.serviceWorker.register('/sw.js');

  // Re-save existing subscription on each login (handles endpoint rotation)
  const existing = await reg.pushManager.getSubscription();
  if (existing) {
    await saveSubscriptionToBackend(existing);
    return true;
  }

  const res = await fetch('/api/v1/account/push-subscription/vapid-key');
  if (!res.ok) return false;
  const { public_key } = await res.json() as { public_key: string };

  const sub = await reg.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey: urlBase64ToUint8Array(public_key),
  });

  await saveSubscriptionToBackend(sub);
  return true;
}

/**
 * Unsubscribes the browser from Web Push and clears the subscription on the backend.
 */
export async function unsubscribe(): Promise<void> {
  if (!('serviceWorker' in navigator)) return;

  const reg = await navigator.serviceWorker.getRegistration('/sw.js');
  if (!reg) return;

  const sub = await reg.pushManager.getSubscription();
  if (sub) {
    await sub.unsubscribe();
  }

  // Clear from backend by saving null-equivalent empty object
  await apiFetch('/api/v1/account/push-subscription', {
    method: 'POST',
    body: JSON.stringify({ subscription: {} }),
  });
}

/** Returns the current Notification permission state. */
export function getPermissionState(): NotificationPermission | 'unsupported' {
  if (!('Notification' in window)) return 'unsupported';
  return Notification.permission;
}

export interface InAppPushPayload {
  title: string;
  body: string;
  task_id?: string;
}

/**
 * Listens for push notifications forwarded by the service worker while the app
 * is in the foreground. Returns a cleanup function to remove the listener.
 */
export function listenForInAppPushes(
  onPush: (payload: InAppPushPayload) => void,
): () => void {
  if (!('serviceWorker' in navigator)) return () => {};

  const handler = (event: MessageEvent) => {
    if (event.data?.type === 'PUSH_RECEIVED') {
      onPush(event.data.data as InAppPushPayload);
    }
  };

  navigator.serviceWorker.addEventListener('message', handler);
  return () => navigator.serviceWorker.removeEventListener('message', handler);
}
