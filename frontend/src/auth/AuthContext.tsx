import { useEffect, useMemo, useState } from "react";

import type { PropsWithChildren } from "react";

import { getCurrentUser, login as loginRequest } from "../services/authService";
import { AuthContext } from "./AuthContextDefinition";
import { AUTH_SESSION_EXPIRED_EVENT, clearSession, getAccessToken, setAccessToken } from "./tokenStorage";
import type { AuthUser } from "../types/auth";

export function AuthProvider({ children }: PropsWithChildren) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isBootstrapping, setIsBootstrapping] = useState(true);

  useEffect(() => {
    async function bootstrap() {
      const token = getAccessToken();
      if (!token) {
        setIsBootstrapping(false);
        return;
      }

      try {
        const me = await getCurrentUser();
        setUser(me);
      } catch {
        clearSession();
        setUser(null);
      } finally {
        setIsBootstrapping(false);
      }
    }

    void bootstrap();
  }, []);

  useEffect(() => {
    const handleExpiredSession = () => setUser(null);
    window.addEventListener(AUTH_SESSION_EXPIRED_EVENT, handleExpiredSession);
    return () => window.removeEventListener(AUTH_SESSION_EXPIRED_EVENT, handleExpiredSession);
  }, []);

  async function login(email: string, password: string) {
    const token = await loginRequest({ email, password });
    setAccessToken(token.access_token);
    const me = await getCurrentUser();
    setUser(me);
  }

  function logout() {
    clearSession();
    setUser(null);
  }

  const value = useMemo(
    () => ({
      user,
      isAuthenticated: Boolean(user),
      isBootstrapping,
      login,
      logout,
    }),
    [isBootstrapping, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
