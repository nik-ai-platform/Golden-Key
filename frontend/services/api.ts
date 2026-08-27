import { getToken, logout } from "./session";
import type { LoginRequest, LoginResponse, RegisterRequest } from "../types/auth";

const API_URL = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

export async function authenticatedFetch(url: string, options: RequestInit = {}) {
  return fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      Authorization: `Bearer ${getToken()}`,
    },
  });
}

async function fetchJson(path: string, options?: RequestInit) {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      headers: { "Content-Type": "application/json", ...(options?.headers || {}) },
      ...options,
    });
  } catch {
    throw new Error("Unable to connect to Golden Key API.");
  }

  if (!response.ok) {
    const data = await response.json().catch(() => null) as { detail?: string } | null;
    if (response.status === 401) {
      logout();
      throw new Error("Your session has expired. Please sign in again.");
    }
    if (response.status === 403) {
      throw new Error(data?.detail ?? "You do not have access to this feature.");
    }
    throw new Error(data?.detail ?? `Request failed (${response.status})`);
  }

  return response.json();
}

export function loginUser(data: LoginRequest): Promise<LoginResponse> {
  return fetchJson("/auth/login", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function registerUser(data: RegisterRequest) {
  return fetchJson("/auth/register", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export function savePrediction(predictionId: number, token = getToken()) {
  return fetchJson("/users/save-prediction", {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    body: JSON.stringify({ prediction_id: predictionId }),
  });
}

export function getSavedPicks(token = getToken()) {
  return fetchJson("/product/me/saved-picks", {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  });
}

export function getProfile(token = getToken()) {
  return fetchJson("/users/me", {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  });
}

export async function getPredictions() {
  const response = await fetch(`${API_URL}/predictions/`, {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error("Failed to load predictions");
  }

  return response.json();
}

export async function runPipeline() {
  const response = await fetch(`${API_URL}/pipeline/run`, {
    method: "POST",
  });

  if (!response.ok) {
    throw new Error("Pipeline failed");
  }

  return response.json();
}

export function getTodaysPredictions() {
  return fetchJson("/intelligence/today");
}

export function getGames() {
  return fetchJson("/games");
}

export function getPortfolio() {
  return fetchJson("/portfolio");
}

export function getResearchUpdates() {
  return fetchJson("/intelligence/research");
}

export function getUserProfile() {
  return fetchJson("/auth/me");
}

export function getTopPicks() {
  return fetchJson("/intelligence/top-picks");
}

export function getIntelligenceReport() {
  return fetchJson("/intelligence/reports");
}

export function getAuth() {
  return fetchJson("/auth/me");
}

export function getMarket() {
  return fetchJson("/market");
}

export function getLive() {
  return fetchJson("/live");
}

export function getModels() {
  return fetchJson("/models");
}

export function getPipelineStatus() {
  return fetchJson("/pipeline/status");
}

export function getPipelineHealth() {
  return fetchJson("/pipeline/health");
}

export async function getBacktests() {
  const response = await authenticatedFetch(`${API_URL}/backtests`, {
    method: "GET",
  });

  if (!response.ok) {
    throw new Error(`Backtests request failed: ${response.status}`);
  }

  return response.json();
}

export async function getModelFactors() {
  const response = await fetch(`${API_URL}/model/factors`, {
    method: "GET",
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Model factors request failed: ${response.status}`);
  }

  return response.json();
}

