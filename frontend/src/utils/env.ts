/**
 * Execution context utilities.
 *
 * Use these helpers to safely guard code that relies on browser-only globals
 * (e.g. `document`, `window`, `navigator`) so it doesn't crash during SSR.
 */

/** Returns `true` when running in a browser (client-side). */
export const isClient = (): boolean => typeof document !== "undefined";

/** Returns `true` when running in Node.js / SSR (server-side). */
export const isServer = (): boolean => !isClient();

/**
 * Logs SSR loader data to the browser console for debugging.
 *
 * Only fires when:
 *  - running in the browser (client-side hydration / navigation)
 *  - `APP_ENV` is `"development"` (evaluated at call-site via import.meta.env)
 *  - the URL contains a `debug` query parameter
 *
 * Usage: call at the end of a route loader, passing the loader's return value.
 *
 * @example
 *   const data = { user, tasks };
 *   debugSsrLog("/ (FlowPage)", data);
 *   return data;
 */
export function debugSsrLog(routeName: string, data: unknown): void {
  if (!isClient()) return;
  if (import.meta.env.MODE !== "development") return;
  if (!new URLSearchParams(window.location.search).has("debug")) return;

  console.groupCollapsed(`[SSR] ${routeName}`);
  console.log(data);
  console.groupEnd();
}
