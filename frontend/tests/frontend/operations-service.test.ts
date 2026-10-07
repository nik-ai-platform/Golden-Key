import { afterEach, describe, expect, it, vi } from "vitest";

import { client } from "../../src/api/client";
import { getWorkerStatus } from "../../src/services/operationsService";

afterEach(() => vi.restoreAllMocks());

describe("read-only operations API", () => {
  it("uses the authenticated client, fixed GET route, and cancellation signal", async () => {
    const data = { observed_at: "now", telemetry_enabled: false, workers: [] };
    const get = vi.spyOn(client, "get").mockResolvedValue({ data });
    const signal = new AbortController().signal;
    expect(await getWorkerStatus(signal)).toBe(data);
    expect(get).toHaveBeenCalledTimes(1);
    expect(get).toHaveBeenCalledWith("/operations/workers", { signal });
  });

  it("propagates errors rather than fabricating healthy evidence", async () => {
    vi.spyOn(client, "get").mockRejectedValue(new Error("Unavailable"));
    await expect(getWorkerStatus()).rejects.toThrow("Unavailable");
  });
});
