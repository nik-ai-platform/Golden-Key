import { fireEvent, render, screen, within } from "@testing-library/react";
import { useQuery } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ProductDashboardPage } from "../../src/pages/ProductDashboardPage";
import type { DailyCardPick, DailyCardResponse, Prediction, TodayPredictionsResponse } from "../../src/types/product";

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

const gamePredictions: Prediction[] = [
  prediction({
    prediction_id: 2,
    game_id: 10,
    home_team: "Buffalo Bills",
    away_team: "Miami Dolphins",
    display_selection: "Buffalo Bills -3.5",
    line_value: -3.5,
  }),
  prediction({
    prediction_id: 7,
    game_id: 10,
    home_team: "Buffalo Bills",
    away_team: "Miami Dolphins",
    market: "moneyline",
    selection: "AWAY",
    display_selection: "Miami Dolphins ML",
    line_value: null,
    american_odds: 145,
  }),
  prediction({
    prediction_id: 4,
    game_id: 10,
    home_team: "Buffalo Bills",
    away_team: "Miami Dolphins",
    market: "total",
    selection: "OVER",
    display_selection: "OVER 47.5",
    line_value: 47.5,
  }),
  prediction({
    prediction_id: 8,
    game_id: 11,
    sport: "NBA",
    home_team: "Denver Nuggets",
    away_team: "Los Angeles Lakers",
    selection: "AWAY",
    display_selection: "Los Angeles Lakers +2.5",
    line_value: 2.5,
  }),
];

function queryResult(data: DailyCardResponse | undefined, isError = false) {
  return {
    data,
    isLoading: false,
    isError,
    refetch: vi.fn(),
  } as ReturnType<typeof useQuery>;
}

function predictionsResult(items: Prediction[]) {
  return {
    data: {
      sport: null,
      slate_date: "2026-09-03",
      count: items.length,
      predictions: items,
    } satisfies TodayPredictionsResponse,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  } as ReturnType<typeof useQuery>;
}

function mockQueries(
  dailyCard: DailyCardResponse | undefined = card,
  predictions: Prediction[] = gamePredictions,
  dailyCardError = false,
) {
  vi.mocked(useQuery).mockImplementation((options) => {
    const queryKey = (options as { queryKey: unknown[] }).queryKey;
    return queryKey[1] === "daily-card"
      ? queryResult(dailyCard, dailyCardError)
      : predictionsResult(predictions);
  });
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
    mockQueries();
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
    expect(screen.getAllByTestId("sportsbook-game")).toHaveLength(2);
    expect(screen.getByRole("heading", { name: "Prediction Summary" })).toBeTruthy();
    expect(screen.getByRole("img", { name: "100% positive edge" })).toBeTruthy();
    expect(screen.getByText("6 measured signals")).toBeTruthy();
    expect(screen.getByText("NPI Top 5")).toBeTruthy();
    expect(screen.getByText("200.0")).toBeTruthy();
    expect(screen.getByText("Avg Confidence")).toBeTruthy();
    expect(screen.getByTestId("best-bet-team-accent")).toBeTruthy();
    expect(screen.getAllByTestId("market-leader-team-accent")).toHaveLength(3);
    expect(screen.getAllByTestId("npi-team-accent")).toHaveLength(5);
  });

  it("renders one dense game board row per game with only real market values", () => {
    renderDashboard();

    const games = screen.getAllByTestId("sportsbook-game");
    expect(games.map((game) => game.dataset.gameId)).toEqual(["10", "11"]);
    const matchupLinks = screen.getAllByRole("link", { name: /View analysis for/ });
    expect(matchupLinks).toHaveLength(2);
    expect(
      within(games[0]).getByRole("link", {
        name: "View analysis for Miami Dolphins at Buffalo Bills",
      }).getAttribute("href"),
    ).toBe("/games/10");
    expect(
      within(games[1]).getByRole("link", {
        name: "View analysis for Los Angeles Lakers at Denver Nuggets",
      }).getAttribute("href"),
    ).toBe("/games/11");
    expect(within(games[0]).getByText("Buffalo Bills")).toBeTruthy();
    expect(within(games[0]).getByText("Miami Dolphins")).toBeTruthy();
    expect(within(games[0]).getByText("-3.5 -110")).toBeTruthy();
    expect(within(games[0]).getByText("+145")).toBeTruthy();
    expect(within(games[0]).getByText("O 47.5 -110")).toBeTruthy();
    expect(screen.getAllByTestId("game-10-spread-value").filter((cell) => cell.dataset.recommended === "true")).toHaveLength(1);
    expect(screen.getAllByTestId("game-10-moneyline-value").every((cell) => cell.dataset.recommended === "false")).toBe(true);
    expect(screen.getAllByTestId("game-11-moneyline-value").every((cell) => cell.textContent === "—")).toBe(true);
    expect(screen.getAllByTestId("game-11-total-value").every((cell) => cell.textContent === "—")).toBe(true);
  });

  it("keeps a long moneyline in Moneyline Value instead of Best Bet", () => {
    renderDashboard();

    expect(within(screen.getByTestId("daily-card-best-bet")).queryByText("Akron ML")).toBeNull();
    const moneyline = screen.getByTestId("daily-card-top-moneyline");
    expect(within(moneyline).getByText("Akron ML")).toBeTruthy();
    expect(moneyline.textContent).toContain("Odds +1300");
  });

  it("derives the edge distribution from measured predictions", () => {
    const mixedPicks = card.featured_picks.map((item, index) => ({
      ...item,
      prediction: {
        ...item.prediction,
        projected_edge: [4, -2, 0, 3][index],
      },
    }));
    mockQueries(
      {
        ...card,
        best_bet: null,
        featured_picks: mixedPicks,
        next_best: [],
      },
      gamePredictions,
    );

    renderDashboard();

    expect(screen.getByRole("img", { name: "50% positive edge" })).toBeTruthy();
    expect(screen.getAllByText("25%", { selector: "p" })).toHaveLength(2);
    expect(screen.getByText("4 measured signals")).toBeTruthy();
  });

  it("shows ranking reasons and requeries when sport changes", () => {
    renderDashboard();
    const bestBet = screen.getByTestId("daily-card-best-bet");
    expect(within(bestBet).getByText("NPI 188.0 / 200")).toBeTruthy();
    expect(within(bestBet).getByText("91.0% confidence")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "NFL" }));
    expect(vi.mocked(useQuery).mock.calls.some(([options]) =>
      JSON.stringify(options.queryKey) === JSON.stringify(["product", "daily-card", "NFL"]),
    )).toBe(true);
  });

  it("renders a focused empty state", () => {
    mockQueries({ ...card, count: 0, best_bet: null }, []);
    renderDashboard();

    expect(screen.getByText("No upcoming predictions are currently available.")).toBeTruthy();
  });

  it("shows Moneyline Value when longshots are the only available picks", () => {
    mockQueries(
      {
        ...card,
        count: 1,
        best_bet: null,
        featured_picks: [card.featured_picks[1]],
        next_best: [],
      },
      [gamePredictions[1]],
    );
    renderDashboard();

    expect(screen.queryByRole("heading", { name: "Best Bet" })).toBeNull();
    expect(
      within(screen.getByTestId("daily-card-top-moneyline")).getByText("Akron ML"),
    ).toBeTruthy();
  });

  it("renders a friendly API error", () => {
    mockQueries(undefined, [], true);
    renderDashboard();

    expect(screen.getByText("Unable to load today's card right now.")).toBeTruthy();
  });
});
