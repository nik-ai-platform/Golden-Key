const SESSION_KEY = "golden_key_access_token";
const LEGACY_SESSION_KEY = "golden_key_token";

export function saveToken(token: string) {
  localStorage.setItem(SESSION_KEY, token);
  localStorage.removeItem(LEGACY_SESSION_KEY);
}

export function getToken() {
  return localStorage.getItem(SESSION_KEY) ?? localStorage.getItem(LEGACY_SESSION_KEY);
}

export function requireToken() {
  const token = getToken();
  if (!token) {
    throw new Error("Please sign in to continue.");
  }
  return token;
}

export function logout() {
  localStorage.removeItem(SESSION_KEY);
  localStorage.removeItem(LEGACY_SESSION_KEY);
}