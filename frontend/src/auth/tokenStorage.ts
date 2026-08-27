const ACCESS_TOKEN_KEY = "golden_key_access_token";
export const AUTH_SESSION_EXPIRED_EVENT = "golden-key:session-expired";

export function getAccessToken(): string | null {
  return localStorage.getItem(ACCESS_TOKEN_KEY);
}

export function setAccessToken(token: string): void {
  localStorage.setItem(ACCESS_TOKEN_KEY, token);
}

export function clearSession(): void {
  localStorage.removeItem(ACCESS_TOKEN_KEY);
}

export function expireSession(): void {
  clearSession();
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event(AUTH_SESSION_EXPIRED_EVENT));
  }
}
