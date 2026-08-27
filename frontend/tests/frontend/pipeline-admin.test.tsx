import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

import PipelineAdminPage from "../../app/admin/pipeline/page";

describe("pipeline admin page", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders status and stages", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/pipeline/status")) {
        return {
          ok: true,
          json: async () => ({
            monitor: { pipeline_status: "idle", success_rate: 100, failures: 0, duration: 1200 },
            stages: ["Games Imported", "Predictions Published"],
          }),
        } as Response;
      }
      return {
        ok: true,
        json: async () => ({
          pipeline_health: [
            { stage: "Games Imported", healthy: true, message: "healthy" },
            { stage: "Predictions Published", healthy: true, message: "healthy" },
          ],
        }),
      } as Response;
    });

    render(<PipelineAdminPage />);

    await waitFor(() => {
      expect(screen.getByText("Pipeline Administration")).toBeTruthy();
      expect(screen.getByText("Games Imported")).toBeTruthy();
      expect(screen.getByText("Predictions Published")).toBeTruthy();
    });
  });
});
