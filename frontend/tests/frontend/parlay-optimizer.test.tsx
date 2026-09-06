import { fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ParlayOptimizerPage } from "../../src/pages/ParlayOptimizerPage";
import {
  optimizeParlay,
  type OptimizedParlay,
  type ParlayLeg,
} from "../../src/services/parlayOptimizerApi";
import { formatProductDate } from "../../src/utils/productFormat";

vi.mock("../../src/services/parlayOptimizerApi", () => ({
  optimizeParlay: vi.fn(),
}));

const baseLeg: ParlayLeg = {
  prediction_id: 1,
  game_id: 10,
  sport: "NCAAF",
  game_date: "2026-09-12T19:30:00",
  home_team: "Kentucky Wildcats",
  away_team: "Alabama Crimson Tide",
  market: "spread",
  selection: "HOME",
  display_selection: "Kentucky Wildcats +10.5",
  line_value: 10.5,
  american_odds: -110,
  npi_score: 168,
  confidence_score: 84,
  simulation_probability: 76,
  projected_edge: 7.2,
  risk_level: "LOW",
  parlay_score: 91,
  reasoning: "Projected market edge: 7.2%. Strong model agreement and market edge.",
  sportsbook: "Test Book",
  odds_observed_at: "2026-09-01T12:00:00Z",
};

function leg(overrides: Partial<ParlayLeg>): ParlayLeg {
  return { ...baseLeg, ...overrides };
}

const result: OptimizedParlay = {
  leg_count: 6,
  generated_at: "2026-09-01T12:00:00Z",
  horizon_days: 7,
  sport: null,
  legs: [
    baseLeg,
    leg({
      prediction_id: 2,
      game_id: 11,
      game_date: "2026-09-12T16:00:00Z",
      home_team: "Oklahoma State Cowboys",
      away_team: "Oregon Ducks",
      display_selection: "Oregon Ducks -22.5",
      line_value: -22.5,
      selection: "AWAY",
    }),
    leg({
      prediction_id: 3,
      game_id: 12,
      game_date: "2026-09-13T04:00:00Z",
      home_team: "Hawaii Rainbow Warriors",
      away_team: "New Mexico State Aggies",
      market: "moneyline",
      display_selection: "Hawaii Rainbow Warriors ML -395",
      line_value: null,
      american_odds: -395,
    }),
    leg({
      prediction_id: 4,
      game_id: 13,
      game_date: "2026-09-12T23:30:00Z",
      home_team: "Iowa Hawkeyes",
      away_team: "Iowa State Cyclones",
      market: "total",
      selection: "OVER",
      display_selection: "Iowa State Cyclones at Iowa Hawkeyes OVER 41.5",
      line_value: 41.5,
    }),
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
    expect(screen.getByText("Kentucky Wildcats +10.5")).toBeTruthy();
    expect(screen.getAllByText("Strong model agreement and market edge.")).toHaveLength(4);
    expect(screen.queryByText(/projected market edge/i)).toBeNull();
    expect(screen.queryByText("Edge")).toBeNull();
    expect(screen.queryByText("Average Edge")).toBeNull();
    expect(screen.getAllByText("NPI")).toHaveLength(4);
    expect(screen.getAllByText("Confidence")).toHaveLength(4);
    expect(screen.getByText("Combined Odds")).toBeTruthy();
    expect(screen.getByText("+4200")).toBeTruthy();
    expect(screen.getByText("Risk")).toBeTruthy();
    expect(screen.getByText("Spreads: 3")).toBeTruthy();
    expect(screen.getByText("Totals: 2")).toBeTruthy();
    expect(screen.getByText("Moneylines: 1")).toBeTruthy();
    expect(screen.queryByText(/parlay probability/i)).toBeNull();
  });

  it("shows matchup, local kickoff, and unchanged selections for every market", async () => {
    renderPage();
    fireEvent.click(screen.getByRole("button", { name: "Build Best Parlay" }));

    expect(await screen.findByText("Alabama Crimson Tide at Kentucky Wildcats")).toBeTruthy();
    expect(screen.getByText("Sat, Sep 12 • 3:30 PM EDT")).toBeTruthy();
    expect(screen.getByText("Kentucky Wildcats +10.5")).toBeTruthy();

    expect(screen.getByText("Oregon Ducks at Oklahoma State Cowboys")).toBeTruthy();
    expect(screen.getByText(formatProductDate("2026-09-12T16:00:00Z"))).toBeTruthy();
    expect(screen.getByText("Oregon Ducks -22.5")).toBeTruthy();

    expect(screen.getByText("New Mexico State Aggies at Hawaii Rainbow Warriors")).toBeTruthy();
    expect(screen.getByText(formatProductDate("2026-09-13T04:00:00Z"))).toBeTruthy();
    expect(screen.getByText("Hawaii Rainbow Warriors ML -395")).toBeTruthy();

    expect(screen.getByText("Iowa State Cyclones at Iowa Hawkeyes", { exact: true })).toBeTruthy();
    expect(screen.getByText(formatProductDate("2026-09-12T23:30:00Z"))).toBeTruthy();
    expect(screen.getByText("Iowa State Cyclones at Iowa Hawkeyes OVER 41.5")).toBeTruthy();
    expect(screen.getByText("Test Book · -395")).toBeTruthy();
  });

  it("supports all requested leg counts", () => {
    renderPage();

    for (const count of [2, 4, 6, 8, 10]) {
      expect(screen.getByRole("button", { name: `${count} Leg` })).toBeTruthy();
    }
  });

  it("keeps the no-qualified-parlay state", async () => {
    vi.mocked(optimizeParlay).mockRejectedValueOnce(new Error("No qualified parlay"));
    renderPage();

    fireEvent.click(screen.getByRole("button", { name: "Build Best Parlay" }));

    expect(
      await screen.findByText("No qualified parlay is available for that leg count right now."),
    ).toBeTruthy();
  });
});