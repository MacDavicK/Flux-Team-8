/* Flux service worker — handles Web Push notifications */

self.addEventListener('push', (event) => {
  const data = event.data?.json() ?? {};

  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((windowClients) => {
      // If the app is open and focused, post a message so it can show an in-app banner.
      const focusedClient = windowClients.find((c) => c.focused);
      if (focusedClient) {
        focusedClient.postMessage({ type: 'PUSH_RECEIVED', data });
      }

      // Always show the OS notification (browser ignores it when tab is focused).
      return self.registration.showNotification(data.title ?? 'Flux Reminder', {
        body: data.body ?? '',
        icon: '/favicon-32x32.png',
        badge: '/favicon-16x16.png',
        data: { task_id: data.task_id, task_name: data.task_name },
        actions: data.actions ?? [],
      });
    })
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();

  const { task_id: taskId, task_name: taskName } = event.notification.data ?? {};
  const action = event.action; // 'done' | 'reschedule' | 'missed' | '' (body tap)

  let targetUrl = '/';
  if (action === 'reschedule' && taskId) {
    targetUrl = `/chat?reschedule_task_id=${taskId}&task_name=${encodeURIComponent(taskName ?? '')}`;
  } else if (action === 'done' && taskId) {
    targetUrl = `/?complete_task_id=${taskId}`;
  } else if (action === 'missed' && taskId) {
    targetUrl = `/?missed_task_id=${taskId}`;
  } else if (taskId) {
    // Body tap — open app home
    targetUrl = '/';
  }

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true }).then((windowClients) => {
      // Try to reuse an existing window at the same origin
      for (const client of windowClients) {
        if (new URL(client.url).origin === self.location.origin && 'navigate' in client) {
          return client.navigate(targetUrl).then((c) => c?.focus());
        }
      }
      return clients.openWindow(targetUrl);
    })
  );
});
