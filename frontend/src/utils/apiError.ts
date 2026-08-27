import type { ApiError } from "../api/client";

export function classifyError(error: unknown): {
  kind: "unauthorized" | "server" | "timeout" | "network" | "generic";
  detail?: string;
} {
  const value = error as Partial<ApiError> | undefined;

  if (!value) {
    return { kind: "generic" };
  }

  if (value.status === 401) {
    return { kind: "unauthorized", detail: value.message };
  }

  if (value.status === 408 || value.status === 504) {
    return { kind: "timeout", detail: value.message };
  }

  if (value.status === 0) {
    return { kind: "network", detail: value.message };
  }

  if ((value.status ?? 0) >= 500) {
    return { kind: "server", detail: value.message };
  }

  return { kind: "generic", detail: value.message };
}
