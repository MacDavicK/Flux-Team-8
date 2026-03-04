import { useEffect, useState } from "react";
import { api } from "~/utils/api";

/**
 * Checks if the backend is reachable (calls /health).
 * If unreachable, use ready === false and show a console warning when falling back to mock.
 */
export function useBackendReady(): { ready: boolean; loading: boolean } {
  const [ready, setReady] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api
      .health()
      .then(() => setReady(true))
      .catch(() => {
        setReady(false);
        console.warn(
          "[Flux] Backend unreachable (health check failed). Using mock fallback where available.",
        );
      })
      .finally(() => setLoading(false));
  }, []);

  return { ready, loading };
}
