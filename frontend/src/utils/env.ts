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
