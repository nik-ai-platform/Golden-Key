import type { AxiosAdapter } from "axios";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AUTH_SESSION_EXPIRED_EVENT, clearSession, setAccessToken } from "../../src/auth/tokenStorage";
import { client } from "../../src/api/client";
import { optimizeParlay } from "../../src/services/parlayOptimizerApi";

describe("Parlay Optimizer API request", () => {
  const originalAdapter = client.defaults.adapter;

  beforeEach(() => {
    localStorage.clear();
  });

  afterEach(() => {
    client.defaults.adapter = originalAdapter;
    clearSession();
    vi.restoreAllMocks();
  });

  it("sends the selected count and optional sport with the stored bearer token", async () => {
    let seenConfig: Parameters<AxiosAdapter>[0] | undefined;
    setAccessToken("unit-test-access-token");
    client.defaults.adapter = async (config) => {
      seenConfig = config;
      return {
        data: { ready: true },
        status: 200,
        statusText: "OK",
        headers: {},
        config,
      };
    };

    await optimizeParlay(6, "NCAAF");

    expect(seenConfig?.url).toBe("/parlays/optimize");
    expect(seenConfig?.params).toEqual({ legs: 6, sport: "NCAAF" });
    expect(seenConfig?.headers.get("Authorization")).toBe("Bearer unit-test-access-token");
    expect(seenConfig?.baseURL).toBeTruthy();
  });

  it("does not issue an authorization header when no session token exists", async () => {
    let hasAuthorization = false;
    client.defaults.adapter = async (config) => {
      hasAuthorization = config.headers.has("Authorization");
      return {
        data: { ready: true },
        status: 200,
        statusText: "OK",
        headers: {},
        config,
      };
    };

    await optimizeParlay(4);

    expect(hasAuthorization).toBe(false);
  });

  it("expires the stored session and reports 401 from the authenticated API", async () => {
    setAccessToken("unit-test-expired-token");
    const expired = vi.fn();
    window.addEventListener(AUTH_SESSION_EXPIRED_EVENT, expired);
    client.defaults.adapter = async (config) => {
      throw {
        config,
        response: {
          status: 401,
          data: { detail: "Token expired" },
          headers: {},
          config,
        },
      };
    };

    await expect(optimizeParlay(6)).rejects.toMatchObject({
      status: 401,
      message: "Your session has expired. Please sign in again.",
    });

    expect(localStorage.getItem("golden_key_access_token")).toBeNull();
    expect(expired).toHaveBeenCalledOnce();
    window.removeEventListener(AUTH_SESSION_EXPIRED_EVENT, expired);
  });
});
