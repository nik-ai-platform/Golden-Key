import axios from "axios";

import { expireSession, getAccessToken } from "../auth/tokenStorage";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? (import.meta.env.DEV ? "http://localhost:8000/api/v1" : "/api/v1");

export type ApiError = {
  status: number;
  message: string;
};

export function getApiErrorMessage(data: unknown, status: number): string {
  if (typeof data === "object" && data !== null && "detail" in data) {
    const detail = (data as { detail?: unknown }).detail;

    if (typeof detail === "string" && detail.trim()) {
      return detail;
    }

    if (Array.isArray(detail)) {
      const messages = detail
        .map((item) => {
          if (
            typeof item === "object" &&
            item !== null &&
            "msg" in item &&
            typeof item.msg === "string"
          ) {
            return item.msg.trim();
          }

          return null;
        })
        .filter((message): message is string => Boolean(message));

      if (messages.length > 0) {
        return messages.join(". ");
      }
    }
  }

  return `Request failed (${status})`;
}

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
    const defaultMessage = `Request failed (${status})`;
    const apiMessage = getApiErrorMessage(error.response?.data, status);
    const message = timedOut
      ? "Request timed out"
      : isNetworkError
        ? "Unable to connect to Golden Key API."
        : status === 401
          ? "Your session has expired. Please sign in again."
          : apiMessage !== defaultMessage
            ? apiMessage
            : status === 403
              ? "You do not have access to this feature."
              : defaultMessage;

    if (status === 401) {
      expireSession();
    }

    return Promise.reject({
      status: isNetworkError ? (timedOut ? 408 : 0) : status,
      message,
    } satisfies ApiError);
  },
);
