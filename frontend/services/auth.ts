import { saveToken, logout as clearSession, getToken as readToken } from "./session";

const API_URL =
  (typeof process !== "undefined" ? process.env?.NEXT_PUBLIC_API_URL : undefined) ||
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_API_URL ||
  "http://localhost:8000/api/v1";

type AuthPayload = {
  email: string;
  password: string;
  username?: string;
  name?: string;
};

export async function registerUser(data: { email: string; username: string; password: string }) {
  const response = await fetch(`${API_URL}/auth/register`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error("Registration failed");
  }

  return response.json();
}

export async function loginUser(data: { email: string; password: string }) {
  const response = await fetch(`${API_URL}/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error("Login failed");
  }

  return response.json();
}

export async function login(payload: AuthPayload) {
  const data = await loginUser({ email: payload.email, password: payload.password });
  if (data?.access_token) {
    saveToken(data.access_token);
  }
  return data;
}

export async function register(payload: AuthPayload) {
  const data = await registerUser({
    email: payload.email,
    username: payload.username ?? payload.name ?? payload.email,
    password: payload.password,
  });
  if (data?.access_token) {
    saveToken(data.access_token);
  }
  return data;
}

export function logout() {
  clearSession();
}

export function getSessionToken(): string | null {
  return readToken();
}

export function isAuthenticated(): boolean {
  return Boolean(getSessionToken());
}

export function requireAuth(path = "/login"): string | null {
  return isAuthenticated() ? null : path;
}
