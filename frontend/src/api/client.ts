import axios from "axios";

import { expireSession, getAccessToken } from "../auth/tokenStorage";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? (import.meta.env.DEV ? "http://localhost:8000/api/v1" : "/api/v1");

export type ApiError = {
  status: number;
  message: string;
};

export const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    "Content-Type": "application/json",
  },
});

client.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

client.interceptors.response.use(
  (response) => response,
  (error) => {
    const isNetworkError = !error.response;
    const timedOut = error.code === "ECONNABORTED";
    const status = error.response?.status ?? 500;
    const detail = error.response?.data?.detail;
    const message = timedOut
      ? "Request timed out"
      : isNetworkError
        ? "Unable to connect to Golden Key API."
        : status === 401
          ? "Your session has expired. Please sign in again."
          : typeof detail === "string"
            ? detail
            : status === 403
              ? "You do not have access to this feature."
              : `Request failed (${status})`;

    if (status === 401) {
      expireSession();
    }

    return Promise.reject({
      status: isNetworkError ? (timedOut ? 408 : 0) : status,
      message,
    } satisfies ApiError);
  },
);
