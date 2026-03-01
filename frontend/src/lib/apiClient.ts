/**
 * Authenticated fetch wrapper.
 * Injects the Supabase JWT as Authorization: Bearer <token> on every request.
 *
 * The token lives in module-level memory only — never in localStorage or cookies
 * readable by JS. It is hydrated once on React mount via serverGetAccessToken()
 * in AuthContext, and cleared on logout.
 */
import { isClient } from "~/utils/env";

type FetchInput = Parameters<typeof fetch>[0];
type FetchInit = Parameters<typeof fetch>[1];

// In-memory token store. Populated by AuthContext after the server function
// reads the httpOnly session cookie. Cleared on logout or page refresh.
let _inMemoryToken: string | null = null;

export function setInMemoryToken(token: string | null) {
  _inMemoryToken = token;
}

export function getInMemoryToken(): string | null {
  return _inMemoryToken;
}

export async function apiFetch(
  input: FetchInput,
  init: FetchInit = {},
): Promise<Response> {
  const headers = new Headers(init.headers);

  if (isClient() && _inMemoryToken) {
    headers.set("Authorization", `Bearer ${_inMemoryToken}`);
  }

  if (!headers.has("Content-Type") && init.body) {
    headers.set("Content-Type", "application/json");
  }

  return fetch(input, { ...init, headers });
}
