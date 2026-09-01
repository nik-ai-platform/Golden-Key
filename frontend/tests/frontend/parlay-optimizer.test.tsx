import { fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ParlayOptimizerPage } from "../../src/pages/ParlayOptimizerPage";
import { optimizeParlay } from "../../src/services/parlayOptimizerApi";

vi.mock("../../src/services/parlayOptimizerApi", () => ({
  optimizeParlay: vi.fn(),
}));

const result = {
  leg_count: 6,
  generated_at: "2026-09-01T12:00:00",
  horizon_days: 7,
  sport: null,
  legs: [
    {
      prediction_id: 1,
      game_id: 10,
      sport: "NFL",
      game_date: "2026-09-05T19:30:00",
      home_team: "Dallas",
      away_team: "New York",
      market: "spread" as const,
      selection: "HOME" as const,
      display_selection: "Dallas -4.5",
      line_value: -4.5,
      american_odds: -110,
      npi_score: 168,
      confidence_score: 84,
      simulation_probability: 76,
      projected_edge: 7.2,
      risk_level: "LOW",
      parlay_score: 91,
      reasoning: "Strong model agreement and market edge.",
      sportsbook: "Test Book",
      odds_observed_at: "2026-09-01T12:00:00",
    },
  ],
  average_npi: 166,
  average_confidence: 83,
  average_projected_edge: 6.3,
  combined_american_odds: 4200,
  risk_level: "MEDIUM",
  market_mix: { spread: 3, total: 2, moneyline: 1 },
};

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <ParlayOptimizerPage />
    </QueryClientProvider>,
  );
}

describe("Parlay Optimizer", () => {
  beforeEach(() => {
    vi.mocked(optimizeParlay).mockResolvedValue(result);
  });

  it("builds the selected leg count and explains qualified legs", async () => {
    renderPage();

    fireEvent.click(screen.getByRole("button", { name: "Build Best Parlay" }));

    expect(await screen.findByText("6-Leg Optimized Parlay")).toBeTruthy();
    expect(
      screen.getByText("Optimized from qualifying games in the next 7 days"),
    ).toBeTruthy();
    expect(optimizeParlay).toHaveBeenCalledWith(6);
    expect(screen.getByText("Dallas -4.5")).toBeTruthy();
    expect(screen.getByText("Strong model agreement and market edge.")).toBeTruthy();
    expect(screen.getByText("Spreads: 3")).toBeTruthy();
    expect(screen.getByText("Totals: 2")).toBeTruthy();
    expect(screen.getByText("Moneylines: 1")).toBeTruthy();
    expect(screen.queryByText(/parlay probability/i)).toBeNull();
  });

  it("supports all requested leg counts", () => {
    renderPage();

    for (const count of [2, 4, 6, 8, 10]) {
      expect(screen.getByRole("button", { name: `${count} Leg` })).toBeTruthy();
    }
  });
});