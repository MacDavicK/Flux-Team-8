/// <reference types="vite/client" />

import "./instrument";
import * as Sentry from "@sentry/react";
import { StartClient } from "@tanstack/react-start/client";
import { hydrateRoot } from "react-dom/client";

hydrateRoot(document, <StartClient />, {
  onRecoverableError: Sentry.reactErrorHandler(),
});
