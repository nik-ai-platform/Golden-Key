import { vi } from "vitest";

const responses: Record<string, unknown> = {
  "/predictions/": [],
  "/backtests": { runs: [] },
  "/model/factors": { top_factors: [], version: "test" },
  "/users/me": {
    id: 1,
    email: "test@example.com",
    username: "Test User",
    premium: false,
  },
};

export function installLegacyApiMock() {
  return vi.spyOn(globalThis, "fetch").mockImplementation(async (input) => {
    const url = String(input);
    const path = Object.keys(responses).find((candidate) =>
      url.endsWith(candidate),
    );

    if (!path) {
      throw new Error(`Unexpected test API request: ${url}`);
    }

    return {
      ok: true,
      status: 200,
      json: async () => responses[path],
    } as Response;
  });
}