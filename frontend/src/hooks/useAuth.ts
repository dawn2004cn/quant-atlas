import { useCallback, useEffect, useState } from "react";
import { fetchCurrentUser, probeSessionAuth } from "../lib/api";

export type AuthMode = "session" | "jwt" | "none";

export function useAuth() {
  const [mode, setMode] = useState<AuthMode>("none");
  const [username, setUsername] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      // Try JWT auth (httpOnly cookie set by /api/v2/auth/token)
      try {
        const user = await fetchCurrentUser();
        setMode("jwt");
        setUsername(user.username);
        return;
      } catch {
        // no valid JWT cookie, fall through to session auth
      }
      const sessionOk = await probeSessionAuth();
      if (sessionOk) {
        setMode("session");
        setUsername(null);
        return;
      }
      setMode("none");
      setUsername(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { mode, username, loading, refresh, isAuthenticated: mode !== "none" };
}
