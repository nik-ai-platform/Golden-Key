import { fireEvent, render, screen, within } from "@testing-library/react";
import { useQuery } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ProductDashboardPage } from "../../src/pages/ProductDashboardPage";
import type { Prediction, TodayPredictionsResponse } from "../../src/types/product";

vi.mock("@tanstack/react-query", () => ({
  useQuery: vi.fn(),
}));

vi.mock("../../src/components/SavePickButton", () => ({
  SavePickButton: () => <button type="button">Save pick</button>,
}));

function future(hours: number): string {
  return new Date(Date.now() + hours * 60 * 60 * 1000).toISOString();
}

function prediction(overrides: Partial<Prediction>): Prediction {
  return {
    prediction_id: 1,
    game_id: 1,
    sport: "NFL",
    home_team: "Philadelphia Eagles",
    away_team: "Dallas Cowboys",
    game_date: future(6),
    market: "spread",
    selection: "HOME",
    display_selection: "Philadelphia Eagles -3.5",
    line_value: -3.5,
    american_odds: -110,
    model_version: "NPI-4.0",
    npi_score: 190,
    confidence_score: 82,
    simulation_probability: 61,
    projected_edge: 8,
    risk_level: "LOW",
    reasoning: null,
    ...overrides,
  };
}

const predictions = [
  prediction({ prediction_id: 1, game_id: 1, npi_score: 190 }),
  prediction({ prediction_id: 2, game_id: 2, sport: "NBA", home_team: "Boston Celtics", away_team: "New York Knicks", game_date: future(2), market: "moneyline", selection: "AWAY", display_selection: "New York Knicks ML", american_odds: 125, npi_score: 180 }),
  prediction({ prediction_id: 3, game_id: 3, sport: "NCAAF", home_team: "Georgia Bulldogs", away_team: "Clemson Tigers", game_date: future(4), market: "total", selection: "OVER", display_selection: "OVER 52.5", npi_score: 170 }),
  prediction({ prediction_id: 4, game_id: 1, market: "moneyline", selection: "HOME", display_selection: "Philadelphia Eagles ML", npi_score: 160 }),
  prediction({ prediction_id: 5, game_id: 4, sport: "WNBA", home_team: "New York Liberty", away_team: "Las Vegas Aces", game_date: future(1), display_selection: "New York Liberty -2.5", npi_score: 150 }),
  prediction({ prediction_id: 6, game_id: 5, sport: "NCAAB", home_team: "Duke Blue Devils", away_team: "UNC Tar Heels", game_date: future(3), market: "total", display_selection: "UNDER 145.5", npi_score: 140 }),
  prediction({ prediction_id: 7, game_id: 6, game_date: future(5), display_selection: "Kansas City Chiefs -4.5", npi_score: 130 }),
  prediction({ prediction_id: 8, game_id: 7, game_date: future(-2), display_selection: "Past HOME", npi_score: 999 }),
];

function queryResult(data: TodayPredictionsResponse | undefined, isError = false) {
  return {
    data,
    isLoading: false,
    isError,
    refetch: vi.fn(),
  } as ReturnType<typeof useQuery>;
}

function renderDashboard() {
  return render(
    <MemoryRouter>
      <ProductDashboardPage />
    </MemoryRouter>,
  );
}

describe("best picks dashboard", () => {
  beforeEach(() => {
    vi.mocked(useQuery).mockReturnValue(
      queryResult({ sport: null, count: predictions.length, predictions }),
    );
  });

  it("ranks five future top picks with complete actionable details", () => {
    renderDashboard();

    const topPicks = screen.getAllByTestId("top-pick");
    expect(topPicks).toHaveLength(5);
    expect(within(topPicks[0]).getByText("Dallas Cowboys @ Philadelphia Eagles")).toBeTruthy();
    expect(within(topPicks[0]).getByText("Philadelphia Eagles -3.5")).toBeTruthy();
    expect(within(topPicks[0]).getByText("Odds -110")).toBeTruthy();
    expect(within(topPicks[1]).getByText("New York Knicks ML")).toBeTruthy();
    expect(within(topPicks[1]).getByText("Odds +125")).toBeTruthy();
    expect(within(topPicks[2]).getByText("OVER 52.5")).toBeTruthy();
    expect(screen.queryByText("Past HOME")).toBeNull();
    expect(within(topPicks[0]).queryByText("HOME")).toBeNull();
    expect(within(topPicks[0]).getByRole("button", { name: "Save pick" })).toBeTruthy();
    expect(
      within(topPicks[0])
        .getByRole("link", { name: /view game analysis/i })
        .getAttribute("href"),
    ).toBe("/games/1");
  });

  it("selects the strongest pick per market", () => {
    renderDashboard();

    expect(within(screen.getByTestId("best-market-spread")).getByText("Philadelphia Eagles -3.5")).toBeTruthy();
    expect(within(screen.getByTestId("best-market-moneyline")).getByText("New York Knicks ML")).toBeTruthy();
    expect(within(screen.getByTestId("best-market-total")).getByText("OVER 52.5")).toBeTruthy();
  });

  it("shows five unique upcoming games ordered by date", () => {
    renderDashboard();

    const games = screen.getAllByTestId("upcoming-game");
    expect(games).toHaveLength(5);
    expect(games.map((game) => game.getAttribute("data-game-id"))).toEqual([
      "4",
      "2",
      "5",
      "3",
      "6",
    ]);
  });

  it("filters every dashboard section by sport", () => {
    renderDashboard();
    fireEvent.click(screen.getByRole("button", { name: "NFL" }));

    for (const topPick of screen.getAllByTestId("top-pick")) {
      expect(topPick.textContent).toContain("NFL");
    }
    expect(screen.getByTestId("best-market-moneyline").textContent).toContain("Philadelphia Eagles ML");
    expect(screen.getByTestId("best-market-total").textContent).toContain("No Total pick available.");
    expect(screen.getAllByTestId("upcoming-game").map((game) => game.getAttribute("data-game-id"))).toEqual(["6", "1"]);
  });

  it("renders a focused empty state", () => {
    vi.mocked(useQuery).mockReturnValue(
      queryResult({ sport: null, count: 0, predictions: [] }),
    );
    renderDashboard();

    expect(screen.getByText("No upcoming predictions are currently available.")).toBeTruthy();
  });

  it("renders a friendly API error", () => {
    vi.mocked(useQuery).mockReturnValue(queryResult(undefined, true));
    renderDashboard();

    expect(screen.getByText("Unable to load predictions right now.")).toBeTruthy();
  });
});