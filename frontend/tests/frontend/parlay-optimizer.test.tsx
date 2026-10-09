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
  selection_reason: "Included in the highest-scoring eligible combination.",
  reasoning: "Projected market edge: 7.2%. Strong model agreement and market edge.",
  sportsbook: "Test Book",
  odds_observed_at: "2026-09-01T12:00:00Z",
};

function leg(overrides: Partial<ParlayLeg>): ParlayLeg {
  return { ...baseLeg, ...overrides };
}

const result: OptimizedParlay = {
  leg_count: 6,
  requested_leg_count: 6,
  adjustment_reason: null,
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
      screen.getByText("Optimized from qualifying games in the next 7 days · All sports"),
    ).toBeTruthy();
    expect(optimizeParlay).toHaveBeenCalledWith(6, undefined);
    expect(screen.getByText("Kentucky Wildcats +10.5")).toBeTruthy();
    expect(screen.getAllByText("Strong model agreement and market edge.")).toHaveLength(4);
    expect(screen.queryByText(/projected market edge/i)).toBeNull();
    expect(screen.queryByText("Edge")).toBeNull();
    expect(screen.queryByText("Average Edge")).toBeNull();
    expect(screen.getAllByText("NPI")).toHaveLength(4);
    expect(screen.getAllByText("Confidence Rating")).toHaveLength(4);
    expect(screen.getAllByText("Model Probability")).toHaveLength(4);
    expect(screen.getAllByText("Why selected")).toHaveLength(4);
    expect(screen.getAllByText("Included in the highest-scoring eligible combination.")).toHaveLength(4);
    expect(screen.queryByText("Parlay Score")).toBeNull();
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
    expect(screen.getAllByText(/Quoted /)).toHaveLength(4);
    expect(screen.getByText(/do not establish independence across games/i)).toBeTruthy();
  });

  it("supports all requested leg counts and optional sport filtering", async () => {
    renderPage();

    for (const count of [2, 4, 6, 8, 10]) {
      expect(screen.getByRole("button", { name: `${count} Leg` })).toBeTruthy();
    }
    const sportFilter = screen.getByRole("combobox", { name: "Sport" });
    fireEvent.mouseDown(sportFilter);
    fireEvent.click(await screen.findByRole("option", { name: "NCAAF" }));
    fireEvent.click(screen.getByRole("button", { name: "Build Best Parlay" }));

    expect(await screen.findByText("6-Leg Optimized Parlay")).toBeTruthy();
    expect(optimizeParlay).toHaveBeenCalledWith(6, "NCAAF");
  });

  it("keeps the no-qualified-parlay state", async () => {
    const message = "Only 1 distinct game has a valid quoted pick with a fresh matching sportsbook line in the next 7 days for NCAAF; at least 2 distinct games are required. Choose All sports or another sport.";
    vi.mocked(optimizeParlay).mockRejectedValueOnce({ status: 422, message });
    renderPage();

    fireEvent.click(screen.getByRole("button", { name: "Build Best Parlay" }));

    expect(await screen.findByText(message)).toBeTruthy();
    expect(screen.getByRole("combobox", { name: "Sport" })).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Retry" })).toBeNull();
  });

  it("explains when a smaller valid parlay is returned", async () => {
    const smallerResult = {
      ...result,
      leg_count: 4,
      requested_leg_count: 6,
      adjustment_reason: "You requested 6 legs. The best-scoring valid combination under the current quoted odds, distinct-game, and market-mix requirements has 4 legs.",
      legs: result.legs.slice(0, 4),
    };
    vi.mocked(optimizeParlay).mockResolvedValueOnce(smallerResult);
    renderPage();

    fireEvent.click(screen.getByRole("button", { name: "Build Best Parlay" }));

    expect(await screen.findByText("4-Leg Optimized Parlay")).toBeTruthy();
    expect(screen.getByText(smallerResult.adjustment_reason)).toBeTruthy();
    expect(screen.getAllByTestId(/parlay-leg-card/)).toHaveLength(4);
  });

  it.each([0, 403, 422, 500])("does not present an API %s failure as an empty result", async (status) => {
    vi.mocked(optimizeParlay).mockRejectedValueOnce({ status, message: "Request failed" });
    renderPage();
    fireEvent.click(screen.getByRole("button", { name: "Build Best Parlay" }));
    expect(await screen.findByText("Unable to build the parlay. Check your connection or access and try again.")).toBeTruthy();
    expect(screen.queryByText("No qualified parlay is available for that leg count right now.")).toBeNull();
    expect(screen.getByRole("button", { name: "Retry" })).toBeTruthy();
  });

  it("treats the known market-mix eligibility failure as an empty state", async () => {
    const message = "The available quoted picks cannot form a 2-leg parlay without repeating a game or violating the market mix. Choose All sports or another sport to broaden the eligible games.";
    vi.mocked(optimizeParlay).mockRejectedValueOnce({ status: 422, message });
    renderPage();
    fireEvent.click(screen.getByRole("button", { name: "Build Best Parlay" }));
    expect(await screen.findByText(message)).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Retry" })).toBeNull();
  });

  it("renders unavailable risk and a deprecated null edge without fabricating metrics", async () => {
    vi.mocked(optimizeParlay).mockResolvedValueOnce({
      ...result,
      risk_level: "unavailable",
      average_projected_edge: null,
      average_projected_edge_deprecated: true,
      average_model_probability: 76,
    });
    renderPage();
    fireEvent.click(screen.getByRole("button", { name: "Build Best Parlay" }));
    expect(await screen.findByText("Unavailable")).toBeTruthy();
    expect(screen.queryByText("Average Edge")).toBeNull();
    expect(screen.queryByText(/parlay probability/i)).toBeNull();
    expect(screen.getByText("83.0")).toBeTruthy();
  });
});