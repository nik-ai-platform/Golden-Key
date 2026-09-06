import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ProductGamesPage } from "../../src/pages/ProductGamesPage";
import { getUpcomingPredictions } from "../../src/services/productApi";
import type { Prediction, UpcomingPredictionsResponse } from "../../src/types/product";

vi.mock("../../src/services/productApi", () => ({
  getUpcomingPredictions: vi.fn(),
}));

vi.mock("../../src/components/SavePickButton", () => ({
  SavePickButton: ({ predictionId }: { predictionId: number }) => (
    <button type="button">Save Pick {predictionId}</button>
  ),
}));

function prediction(overrides: Partial<Prediction>): Prediction {
  return {
    prediction_id: 1,
    game_id: 1,
    sport: "NFL",
    home_team: "Seattle Seahawks",
    away_team: "New England Patriots",
    game_date: "2026-09-07T04:00:00",
    market: "spread",
    selection: "HOME",
    display_selection: "Seattle Seahawks -3.5",
    line_value: -3.5,
    american_odds: -110,
    model_version: "NPI-4.0",
    npi_score: 180,
    confidence_score: 83,
    simulation_probability: 61,
    projected_edge: 8,
    risk_level: "LOW",
    reasoning: null,
    recommendation_eligible: true,
    recommendation_tier: null,
    recommendation_designation: null,
    ...overrides,
  };
}

const predictions = [
  prediction({ prediction_id: 1 }),
  prediction({
    prediction_id: 2,
    market: "moneyline",
    selection: "AWAY",
    display_selection: "New England Patriots ML",
    american_odds: 125,
    npi_score: 170,
  }),
  prediction({
    prediction_id: 3,
    market: "total",
    selection: "OVER",
    display_selection: "OVER 44.5",
    line_value: 44.5,
    npi_score: 160,
  }),
  prediction({
    prediction_id: 4,
    game_id: 2,
    sport: "NBA",
    home_team: "Boston Celtics",
    away_team: "New York Knicks",
    game_date: "2026-09-07T00:30:00",
    display_selection: "Boston Celtics -2.5",
    line_value: -2.5,
    npi_score: 150,
    confidence_score: 72,
  }),
  prediction({
    prediction_id: 5,
    game_id: 2,
    sport: "NBA",
    home_team: "Boston Celtics",
    away_team: "New York Knicks",
    game_date: "2026-09-07T00:30:00",
    market: "moneyline",
    selection: "AWAY",
    display_selection: "New York Knicks ML",
    american_odds: -1000,
    npi_score: 190,
    confidence_score: 85,
    recommendation_eligible: false,
    recommendation_tier: "LOW_VALUE_HEAVY_FAVORITE",
    recommendation_designation: "High Probability — Low Betting Value",
  }),
  prediction({
    prediction_id: 6,
    game_id: 3,
    sport: "NCAAF",
    home_team: "Kentucky Wildcats",
    away_team: "Alabama Crimson Tide",
    game_date: "2026-09-12T19:30:00",
    display_selection: "Kentucky Wildcats +10.5",
    line_value: 10.5,
  }),
];

function response(items: Prediction[]): UpcomingPredictionsResponse {
  return {
    sport: null,
    start_date: "2026-09-06T12:00:00Z",
    end_date: "2026-09-20T12:00:00Z",
    count: items.length,
    predictions: items,
  };
}

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/games"]}>
        <ProductGamesPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("Games decision screen", () => {
  beforeEach(() => {
    vi.mocked(getUpcomingPredictions).mockImplementation(async (sport) =>
      response(
        sport
          ? predictions.filter((item) => item.sport === sport)
          : predictions,
      ),
    );
  });

  it("groups upcoming games by Eastern date in chronological order", async () => {
    renderPage();

    const cards = await screen.findAllByTestId("game-card");
    expect(screen.getByText(/SUN, SEP 6$/)).toBeTruthy();
    expect(screen.getByText(/MON, SEP 7$/)).toBeTruthy();
    expect(screen.getByText(/SAT, SEP 12$/)).toBeTruthy();
    expect(cards).toHaveLength(3);
    expect(cards.map((card) => card.getAttribute("data-game-id"))).toEqual([
      "2",
      "1",
      "3",
    ]);

    const nbaCard = cards[0];
    const nflCard = cards[1];
    expect(within(nbaCard).getByText("New York Knicks @ Boston Celtics")).toBeTruthy();
    expect(within(nflCard).getByText("New England Patriots @ Seattle Seahawks")).toBeTruthy();
    expect(within(nflCard).getByText("NFL")).toBeTruthy();
    expect(within(nbaCard).getByText("Sun, Sep 6 • 8:30 PM EDT")).toBeTruthy();
    expect(within(nflCard).getByText("Mon, Sep 7 • 12:00 AM EDT")).toBeTruthy();
    expect(within(cards[2]).getByText("Sat, Sep 12 • 3:30 PM EDT")).toBeTruthy();

    for (const market of ["Spread", "Moneyline", "Total"]) {
      expect(within(nflCard).getByText(market)).toBeTruthy();
    }
    expect(within(nbaCard).queryByText("Total")).toBeNull();
    expect(within(nflCard).getByText("Seattle Seahawks -3.5")).toBeTruthy();
    expect(within(nflCard).getByText("New England Patriots ML")).toBeTruthy();
    expect(within(nflCard).getByText("OVER 44.5")).toBeTruthy();
    expect(screen.queryByText("HOME")).toBeNull();
    expect(screen.queryByText("AWAY")).toBeNull();
    expect(within(nflCard).getByText("Odds +125")).toBeTruthy();
    expect(within(nflCard).getByText("180.0 / 200")).toBeTruthy();
    expect(within(nflCard).getAllByText("83.0%")).toHaveLength(3);
    expect(within(nflCard).getAllByText("Golden Key Best Pick")).toHaveLength(1);
    expect(within(nbaCard).getAllByText("Golden Key Best Pick")).toHaveLength(1);
    expect(within(nbaCard).getByText("High Probability — Low Betting Value")).toBeTruthy();
    expect(within(nbaCard).getByText("Odds -1000")).toBeTruthy();
    expect(
      within(nbaCard).getByText("Boston Celtics -2.5").parentElement?.textContent,
    ).toContain("Golden Key Best Pick");
    expect(screen.getAllByRole("button", { name: /save pick/i })).toHaveLength(6);
    expect(
      within(nflCard)
        .getByRole("link", { name: /view game analysis/i })
        .getAttribute("href"),
    ).toBe("/games/1");
  });

  it("preserves every sport filter and updates the game list", async () => {
    renderPage();
    await screen.findAllByTestId("game-card");

    for (const sport of ["All", "NFL", "NBA", "NCAAF", "NCAAB", "WNBA"]) {
      expect(screen.getByRole("button", { name: sport })).toBeTruthy();
    }

    fireEvent.click(screen.getByRole("button", { name: "NFL" }));

    await waitFor(() => {
      const cards = screen.getAllByTestId("game-card");
      expect(cards).toHaveLength(1);
      expect(cards[0].getAttribute("data-game-id")).toBe("1");
    });
    expect(getUpcomingPredictions).toHaveBeenLastCalledWith("NFL");
  });

  it("shows the loading state", () => {
    vi.mocked(getUpcomingPredictions).mockImplementation(() => new Promise(() => undefined));
    renderPage();

    expect(screen.getByText("Loading games...")).toBeTruthy();
  });

  it("shows the empty state", async () => {
    vi.mocked(getUpcomingPredictions).mockResolvedValue(response([]));
    renderPage();

    expect(
      await screen.findByText("No upcoming games are currently available."),
    ).toBeTruthy();
  });

  it("shows a friendly error without exposing API details", async () => {
    vi.mocked(getUpcomingPredictions).mockRejectedValue(new Error("database detail"));
    renderPage();

    expect(await screen.findByText("Unable to load games right now.")).toBeTruthy();
    expect(screen.queryByText("database detail")).toBeNull();
  });
});