import { afterEach, describe, expect, it, vi } from "vitest";

import {
  getGames,
  getPipelineHealth,
  getPipelineStatus,
  getPortfolio,
  getResearchUpdates,
  getTodaysPredictions,
  runPipeline,
} from "../../services/api";

describe("api integration layer", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("loads today's predictions", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(
      {
        ok: true,
        json: async () => ({ top_pick: "Chiefs +3" }),
      } as Response,
    );

    const result = await getTodaysPredictions();
    expect(result.top_pick).toBe("Chiefs +3");
    expect(fetchMock).toHaveBeenCalled();
  });

  it("loads games portfolio and research endpoints", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      {
        ok: true,
        json: async () => ({ ok: true }),
      } as Response,
    );

    const games = await getGames();
    const portfolio = await getPortfolio();
    const research = await getResearchUpdates();

    expect(games.ok).toBe(true);
    expect(portfolio.ok).toBe(true);
    expect(research.ok).toBe(true);
  });

  it("loads pipeline endpoints", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      {
        ok: true,
        json: async () => ({ ok: true }),
      } as Response,
    );

    const status = await getPipelineStatus();
    const health = await getPipelineHealth();
    const run = await runPipeline();

    expect(status.ok).toBe(true);
    expect(health.ok).toBe(true);
    expect(run.ok).toBe(true);
  });
});
