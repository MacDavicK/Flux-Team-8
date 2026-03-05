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
        data: { task_id: data.task_id },
        actions: data.actions ?? [],
      });
    })
  );
});

self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const taskId = event.notification.data?.task_id;
  const action = event.action; // 'done', 'reschedule', 'missed'

  if (!taskId || !action) return;

  let url, method;
  if (action === 'done') {
    url = `/api/v1/tasks/${taskId}/complete`;
    method = 'PATCH';
  } else if (action === 'missed') {
    url = `/api/v1/tasks/${taskId}/missed`;
    method = 'PATCH';
  } else {
    // reschedule — focus/open the app
    event.waitUntil(
      clients.matchAll({ type: 'window' }).then((windowClients) => {
        for (const client of windowClients) {
          if ('focus' in client) return client.focus();
        }
        if (clients.openWindow) return clients.openWindow('/');
      })
    );
    return;
  }

  event.waitUntil(fetch(url, { method }).catch(() => {}));
});
