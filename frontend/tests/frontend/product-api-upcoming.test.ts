import { afterEach, describe, expect, it, vi } from "vitest";

import { client } from "../../src/api/client";
import { getTodayPredictions, getUpcomingPredictions } from "../../src/services/productApi";

describe("product prediction API", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("requests upcoming predictions with the existing optional filters", async () => {
    const data = {
      sport: "NCAAF",
      start_date: "2026-09-06T12:00:00Z",
      end_date: "2026-09-20T12:00:00Z",
      count: 0,
      predictions: [],
    };
    const get = vi.spyOn(client, "get").mockResolvedValue({ data });

    await expect(getUpcomingPredictions("NCAAF", true)).resolves.toEqual(data);
    expect(get).toHaveBeenCalledWith("/product/predictions/upcoming", {
      params: { sport: "NCAAF", include_passes: true },
    });
  });

  it("keeps the today endpoint unchanged", async () => {
    const data = {
      sport: null,
      slate_date: "2026-09-06",
      count: 0,
      predictions: [],
    };
    const get = vi.spyOn(client, "get").mockResolvedValue({ data });

    await expect(getTodayPredictions()).resolves.toEqual(data);
    expect(get).toHaveBeenCalledWith("/product/predictions/today", {
      params: { sport: undefined, include_passes: undefined },
    });
  });
});