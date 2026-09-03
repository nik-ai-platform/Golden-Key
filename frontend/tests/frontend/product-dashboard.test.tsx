import { fireEvent, render, screen, within } from "@testing-library/react";
import { useQuery } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ProductDashboardPage } from "../../src/pages/ProductDashboardPage";
import type { DailyCardPick, DailyCardResponse, Prediction } from "../../src/types/product";

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

function pick(role: DailyCardPick["role"], label: string, item: Prediction): DailyCardPick {
  return {
    role,
    label,
    ranking_score: 88,
    ranking_reasons: ["NPI 188.0 / 200", "91.0% confidence", "8.4% projected edge"],
    prediction: item,
  };
}

const card: DailyCardResponse = {
  sport: null,
  generated_at: future(0),
  slate_date: "2026-09-03",
  count: 6,
  best_bet: pick(
    "BEST_BET",
    "Best Bet",
    prediction({
      display_selection: "Georgia -6.5",
      npi_score: 188,
      confidence_score: 91,
      projected_edge: 8.4,
    }),
  ),
  featured_picks: [
    pick(
      "TOP_SPREAD",
      "Top Spread",
      prediction({ prediction_id: 2, game_id: 2, display_selection: "Alabama -4.5" }),
    ),
    pick(
      "TOP_MONEYLINE",
      "Moneyline Value",
      prediction({
        prediction_id: 3,
        game_id: 3,
        market: "moneyline",
        selection: "AWAY",
        display_selection: "Akron ML",
        american_odds: 1300,
        npi_score: 200,
      }),
    ),
    pick(
      "TOP_TOTAL",
      "Top Total",
      prediction({
        prediction_id: 4,
        game_id: 4,
        market: "total",
        selection: "OVER",
        display_selection: "OVER 47.5",
        line_value: 47.5,
      }),
    ),
    pick(
      "VALUE_PLAY",
      "Value Play",
      prediction({
        prediction_id: 5,
        game_id: 5,
        selection: "AWAY",
        display_selection: "Duke +3.5",
        line_value: 3.5,
      }),
    ),
  ],
  next_best: [
    pick(
      "NEXT_BEST",
      "Next Best Pick",
      prediction({ prediction_id: 6, game_id: 6, display_selection: "Texas -2.5" }),
    ),
  ],
};

function queryResult(data: DailyCardResponse | undefined, isError = false) {
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

describe("daily card dashboard", () => {
  beforeEach(() => {
    vi.mocked(useQuery).mockReturnValue(queryResult(card));
  });

  it("renders the primary bet, market roles, value play, and next picks", () => {
    renderDashboard();

    expect(screen.getByRole("heading", { name: "Today's Intelligence" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Best Bet" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Market Leaders" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Model Intelligence" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Today's Games" })).toBeTruthy();
    expect(
      within(screen.getByTestId("daily-card-best-bet")).getByText("Georgia -6.5"),
    ).toBeTruthy();
    expect(
      within(screen.getByTestId("daily-card-top-spread")).getByText("Alabama -4.5"),
    ).toBeTruthy();
    expect(screen.getByTestId("daily-card-best-bet").dataset.emphasis).toBe("premium");
    expect(screen.getAllByTestId("daily-card-top-spread")[0].dataset.emphasis).toBe("featured");
    expect(within(screen.getByTestId("daily-card-top-total")).getByText("OVER 47.5")).toBeTruthy();
    expect(within(screen.getByTestId("daily-game-value-play")).getByText("Duke +3.5")).toBeTruthy();
    expect(screen.getAllByTestId("next-best-pick")).toHaveLength(1);
    expect(screen.getByText("6 ranked signals")).toBeTruthy();
    expect(screen.getByText("NPI Leaders")).toBeTruthy();
  });

  it("keeps a long moneyline in Moneyline Value instead of Best Bet", () => {
    renderDashboard();

    expect(within(screen.getByTestId("daily-card-best-bet")).queryByText("Akron ML")).toBeNull();
    const moneyline = screen.getByTestId("daily-card-top-moneyline");
    expect(within(moneyline).getByText("Akron ML")).toBeTruthy();
    expect(moneyline.textContent).toContain("Odds +1300");
  });

  it("shows ranking reasons and requeries when sport changes", () => {
    renderDashboard();
    const bestBet = screen.getByTestId("daily-card-best-bet");
    expect(within(bestBet).getByText("NPI 188.0 / 200")).toBeTruthy();
    expect(within(bestBet).getByText("91.0% confidence")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "NFL" }));
    expect(vi.mocked(useQuery).mock.calls.at(-1)?.[0].queryKey).toEqual([
      "product",
      "daily-card",
      "NFL",
    ]);
  });

  it("renders a focused empty state", () => {
    vi.mocked(useQuery).mockReturnValue(queryResult({ ...card, count: 0, best_bet: null }));
    renderDashboard();

    expect(screen.getByText("No upcoming predictions are currently available.")).toBeTruthy();
  });

  it("shows Moneyline Value when longshots are the only available picks", () => {
    vi.mocked(useQuery).mockReturnValue(
      queryResult({
        ...card,
        count: 1,
        best_bet: null,
        featured_picks: [card.featured_picks[1]],
        next_best: [],
      }),
    );
    renderDashboard();

    expect(screen.queryByRole("heading", { name: "Best Bet" })).toBeNull();
    expect(
      within(screen.getByTestId("daily-card-top-moneyline")).getByText("Akron ML"),
    ).toBeTruthy();
  });

  it("renders a friendly API error", () => {
    vi.mocked(useQuery).mockReturnValue(queryResult(undefined, true));
    renderDashboard();

    expect(screen.getByText("Unable to load today's card right now.")).toBeTruthy();
  });
});
