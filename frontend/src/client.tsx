/// <reference types="vite/client" />

import { StartClient } from "@tanstack/react-start/client";
import { hydrateRoot } from "react-dom/client";

async function enableMocking() {
  if (import.meta.env.PROD) {
    return;
  }

  const { worker } = await import("./mocks/browser");

  // `worker.start()` returns a Promise that resolves
  // once the Service Worker is up and ready to intercept requests.
  return worker.start({
    onUnhandledRequest: "bypass",
  });
}

enableMocking().then(() => {
  hydrateRoot(document, <StartClient />);
});
