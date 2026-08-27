import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("../src/api/client", () => ({
  client: {
    get: vi.fn(),
    put: vi.fn(),
  },
}));

import { client } from "../src/api/client";
import { updateProfilePreferences } from "../src/services/profileService";

const mockedClient = vi.mocked(client, true);

describe("profile service", () => {
  beforeEach(() => {
    mockedClient.put.mockReset();
  });

  it("sends updated preferences to the backend", async () => {
    mockedClient.put.mockResolvedValue({ data: { ok: true } } as never);

    const payload = {
      user_id: 1,
      risk_level: "aggressive",
      preferred_sports: ["NBA"],
      preferred_bet_types: ["ML"],
      confidence_threshold: 85,
    };

    await updateProfilePreferences(payload);

    expect(mockedClient.put).toHaveBeenCalledWith("/profile/preferences", payload);
  });
});
