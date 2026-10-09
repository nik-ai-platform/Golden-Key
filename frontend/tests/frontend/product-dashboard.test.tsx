import { fireEvent, render, screen, within } from "@testing-library/react";
import { useQuery } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ProductDashboardPage } from "../../src/pages/ProductDashboardPage";
import { SportsbookGamesBoard } from "../../src/components/SportsbookGamesBoard";
import { styleAtBreakpoint } from "./responsiveStyles";
import type { DailyCardPick, DailyCardResponse, Prediction, UpcomingPredictionsResponse } from "../../src/types/product";

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
    recommendation_eligible: true,
    recommendation_tier: null,
    recommendation_designation: null,
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
    game_date: "2026-09-06T20:00:00",
    home_team: "Buffalo Bills",
    away_team: "Miami Dolphins",
    display_selection: "Buffalo Bills -3.5",
    line_value: -3.5,
  }),
  prediction({
    prediction_id: 7,
    game_id: 10,
    game_date: "2026-09-06T20:00:00",
    home_team: "Buffalo Bills",
    away_team: "Miami Dolphins",
    market: "moneyline",
    selection: "HOME",
    display_selection: "Buffalo Bills ML",
    line_value: null,
    american_odds: -1000,
    recommendation_eligible: false,
    recommendation_tier: "LOW_VALUE_HEAVY_FAVORITE",
    recommendation_designation: "High Probability — Low Betting Value",
  }),
  prediction({
    prediction_id: 4,
    game_id: 10,
    game_date: "2026-09-06T20:00:00",
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
    game_date: "2026-09-07T23:30:00",
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
      start_date: "2026-09-06T12:00:00Z",
      end_date: "2026-09-20T12:00:00Z",
      count: items.length,
      predictions: items,
    } satisfies UpcomingPredictionsResponse,
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
      : queryKey[1] === "performance"
        ? { data: { wins: 12, losses: 8, pushes: 2, recent_results: [] }, isLoading: false, isError: false, refetch: vi.fn() } as ReturnType<typeof useQuery>
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
    expect(screen.getByRole("heading", { name: "Upcoming Games" })).toBeTruthy();
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
    expect(screen.queryByRole("heading", { name: "Prediction Summary" })).toBeNull();
    expect(screen.getByText("Model Top Picks")).toBeTruthy();
    const totalPick = screen.getByTestId("npi-pick-label-4");
    expect(within(totalPick).getByText("Dallas Cowboys @ Philadelphia Eagles")).toBeTruthy();
    expect(within(totalPick).getByText("OVER 47.5")).toBeTruthy();
    expect(screen.getByText("200.0")).toBeTruthy();
    expect(screen.getByText("Avg Confidence Rating")).toBeTruthy();
    expect(screen.getByTestId("best-bet-team-accent")).toBeTruthy();
    expect(screen.getAllByTestId("market-leader-team-accent")).toHaveLength(3);
    expect(screen.getAllByTestId("npi-team-accent")).toHaveLength(5);
    expect(screen.getByTestId("npi-pick-label-3").textContent).toBe("Akron ML");
    expect(screen.getByTestId("npi-pick-label-2").textContent).toBe("Alabama -4.5");
  });

  it("places one outcomes panel before picks on mobile and in the desktop sidebar", () => {
    renderDashboard();
    const outcomes = screen.getByTestId("dashboard-outcomes-placement");
    const picks = screen.getByTestId("dashboard-picks-panel");
    expect(outcomes.nextElementSibling).toBe(picks);
    expect(screen.getAllByRole("heading", { name: "Model Outcomes" })).toHaveLength(1);
    expect(styleAtBreakpoint(outcomes, 0, "grid-row")).toBe("1");
    expect(styleAtBreakpoint(picks, 0, "grid-row")).toBe("2");
    expect(styleAtBreakpoint(outcomes, 1200, "grid-column")).toBe("2");
    expect(styleAtBreakpoint(outcomes, 1200, "grid-row")).toBe("1");
    expect(styleAtBreakpoint(picks, 600, "grid-row")).toBe("1");
  });

  it("renders one dense game board row per game with only real market values", () => {
    mockQueries(card, [gamePredictions[3], ...gamePredictions.slice(0, 3)]);
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
    expect(within(games[0]).getAllByText("Buffalo Bills").length).toBeGreaterThan(0);
    expect(within(games[0]).getAllByText("Miami Dolphins").length).toBeGreaterThan(0);
    expect(within(games[0]).getAllByText("-3.5 -110").length).toBeGreaterThan(0);
    expect(within(games[0]).getAllByText("-1000").length).toBeGreaterThan(0);
    expect(within(games[0]).getAllByText("O 47.5 -110").length).toBeGreaterThan(0);
    expect(within(games[0]).getByText("4:00 PM EDT")).toBeTruthy();
    expect(within(games[1]).getByText("7:30 PM EDT")).toBeTruthy();
    expect(
      within(screen.getByTestId("game-10-home-team-row"))
        .getByTestId("game-10-spread-value").dataset.recommended,
    ).toBe("true");
    expect(
      within(screen.getByTestId("game-10-away-team-row"))
        .getByTestId("game-10-spread-value").dataset.recommended,
    ).toBe("false");
    expect(screen.getAllByTestId("game-10-moneyline-value").every((cell) => cell.dataset.recommended === "false")).toBe(true);
    expect(screen.getAllByTestId("game-11-moneyline-value").every((cell) => cell.textContent === "—")).toBe(true);
    expect(screen.getAllByTestId("game-11-total-value").every((cell) => cell.textContent === "—")).toBe(true);
    expect(within(games[0]).getByTestId("game-10-away-team-row")).toBeTruthy();
    expect(within(games[0]).getByTestId("game-10-home-team-row")).toBeTruthy();
    expect(within(games[0]).getByTestId("game-10-away-score").textContent).toBe("—");
    const totalRows = within(games[0]).getAllByTestId("game-10-total-row");
    expect(totalRows).toHaveLength(1);
    expect(within(totalRows[0]).getByText("Game total")).toBeTruthy();
    expect(within(totalRows[0]).getByText("O 47.5 -110")).toBeTruthy();
    for (const game of games) {
      expect(within(game).getAllByTestId(`game-${game.dataset.gameId}-total-row`)).toHaveLength(1);
      expect(within(game).getAllByTestId(`game-${game.dataset.gameId}-total-value`)).toHaveLength(1);
      const [analysis] = within(game).getAllByRole("link", { name: /View analysis for/ });
      expect(within(game).getAllByRole("link", { name: /View analysis for/ })).toHaveLength(1);
      const header = within(game).getByTestId(`game-${game.dataset.gameId}-header`);
      expect(header.contains(analysis)).toBe(true);
      expect(header.contains(within(game).getByText(/PM EDT$/))).toBe(true);
      expect(styleAtBreakpoint(header, 0, "display")).toBe("flex");
      expect(styleAtBreakpoint(header, 900, "display")).toBe("contents");
      expect(getComputedStyle(analysis).minHeight).toBe("44px");
      expect(getComputedStyle(within(analysis).getByText("View matchup analysis")).textDecoration).toBe("underline");
      expect(styleAtBreakpoint(game, 0, "padding-top")).toBe("6px");
      expect(styleAtBreakpoint(game, 0, "margin-bottom")).toBe("12px");
      expect(styleAtBreakpoint(game, 900, "display")).toBe("grid");
      expect(styleAtBreakpoint(game, 900, "padding-top")).toBe("12px");
      const teamRow = within(game).getByTestId(`game-${game.dataset.gameId}-home-team-row`);
      expect(getComputedStyle(teamRow).gap).toBe("1px");
      expect(getComputedStyle(teamRow).paddingTop).toBe("3px");
      const total = within(game).getByTestId(`game-${game.dataset.gameId}-total-row`);
      expect(styleAtBreakpoint(total, 0, "padding-top")).toBe("4px");
      expect(styleAtBreakpoint(total, 0, "margin-top")).toBe("4px");
    }
  });

  it("bounds desktop Model Intelligence rows and increases body/data text only at md", () => {
    renderDashboard();
    const label = screen.getByTestId("npi-pick-label-4");
    const row = label.parentElement!;
    expect(styleAtBreakpoint(row.parentElement!, 900, "max-width")).toBe("640px");
    expect(styleAtBreakpoint(label.lastElementChild!, 900, "font-size")).toBe("1.0625rem");
    expect(styleAtBreakpoint(label.firstElementChild!, 900, "font-size")).toBe("0.9375rem");
    expect(styleAtBreakpoint(row.lastElementChild!, 900, "font-size")).toBe("1.0625rem");
    const odds = screen.getByTestId("game-10-total-value").firstElementChild!;
    expect(styleAtBreakpoint(odds, 0, "font-size")).toBe("0.78rem");
    expect(styleAtBreakpoint(odds, 900, "font-size")).toBe("0.84rem");
  });

  it("labels NPI totals with both teams and the game-level selection", () => {
    const over = pick(
      "TOP_TOTAL",
      "Top Total",
      prediction({
        prediction_id: 20,
        game_id: 20,
        away_team: "New York Jets",
        home_team: "Tennessee Titans",
        market: "total",
        selection: "OVER",
        display_selection: "New York Jets @ Tennessee Titans — OVER 38.5",
        line_value: 38.5,
      }),
    );
    const under = pick(
      "NEXT_BEST",
      "Next Best Pick",
      prediction({
        prediction_id: 21,
        game_id: 21,
        away_team: "Tampa Bay Buccaneers",
        home_team: "Cincinnati Bengals",
        market: "total",
        selection: "UNDER 50.5",
        display_selection: "Tampa Bay Buccaneers @ Cincinnati Bengals — UNDER 50.5",
        line_value: 50.5,
      }),
    );
    mockQueries(
      {
        ...card,
        count: 2,
        best_bet: null,
        featured_picks: [over],
        next_best: [under],
      },
      [],
    );

    renderDashboard();

    for (const [id, matchup, selection] of [
      [20, "New York Jets @ Tennessee Titans", "OVER 38.5"],
      [21, "Tampa Bay Buccaneers @ Cincinnati Bengals", "UNDER 50.5"],
    ] as const) {
      const label = screen.getByTestId(`npi-pick-label-${id}`);
      expect(Array.from(label.children).map((line) => line.textContent)).toEqual([matchup, selection]);
      expect(getComputedStyle(label).overflowWrap).toBe("anywhere");
      expect(getComputedStyle(label.children[0]).color).not.toBe(getComputedStyle(label.children[1]).color);
      expect(getComputedStyle(label.children[1]).fontWeight).toBe("700");
      expect(getComputedStyle(label.children[1]).textOverflow).not.toBe("ellipsis");
    }
  });

  it("reduces the mobile heading by 15–20% while retaining the desktop hierarchy", () => {
    renderDashboard();
    const heading = screen.getByRole("heading", { name: "Today's Intelligence" });
    const mobileSize = styleAtBreakpoint(heading, 0, "font-size");
    const desktopSize = styleAtBreakpoint(heading, 600, "font-size");
    expect(mobileSize).toBe("1.75rem");
    expect(desktopSize).toBe("2.125rem");
    const reduction = 1 - Number.parseFloat(mobileSize) / Number.parseFloat(desktopSize);
    expect(reduction).toBeGreaterThanOrEqual(0.15);
    expect(reduction).toBeLessThanOrEqual(0.20);
    const filters = screen.getByRole("group", { name: "Filter daily card by sport" });
    expect(styleAtBreakpoint(filters, 0, "margin-top")).toBe("8px");
  });

  it("keeps Best Bet metrics in two columns and analysis primary", () => {
    renderDashboard();
    const bestBet = screen.getByTestId("daily-card-best-bet");
    expect(getComputedStyle(within(bestBet).getByTestId("hero-metrics-grid")).gridTemplateColumns)
      .toBe("repeat(2, minmax(0, 1fr))");
    const analysis = within(bestBet).getByRole("link", { name: "View Analysis" });
    expect(analysis.getAttribute("href")).toBe("/games/1");
    expect(analysis.classList.contains("MuiButton-contained")).toBe(true);
    expect(within(bestBet).getByRole("button", { name: "Save pick" })).toBeTruthy();
    expect(within(bestBet).getByText("61.0%")).toBeTruthy();
    expect(within(bestBet).getByText("91.0")).toBeTruthy();
    expect(within(bestBet).getByText("NPI 188")).toBeTruthy();
  });

  it.each(["HOME", "AWAY"])("keeps %s spread and moneyline odds associated with that team", (side) => {
    render(
      <MemoryRouter>
        <SportsbookGamesBoard
          predictions={[
            { ...gamePredictions[0], selection: side, home_score: 0, away_score: 7 },
            { ...gamePredictions[1], selection: side },
            gamePredictions[2],
          ]}
          recommendedPredictionIds={new Set([2])}
        />
      </MemoryRouter>,
    );
    const selected = screen.getByTestId(`game-10-${side.toLowerCase()}-team-row`);
    const opposite = screen.getByTestId(`game-10-${side === "HOME" ? "away" : "home"}-team-row`);
    expect(within(selected).getByTestId("game-10-spread-value").textContent).toBe("-3.5  -110");
    expect(within(selected).getByTestId("game-10-moneyline-value").textContent).toBe("-1000");
    expect(within(opposite).getByTestId("game-10-spread-value").textContent).toBe("—");
    expect(within(opposite).getByTestId("game-10-moneyline-value").textContent).toBe("—");
    expect(screen.getByTestId("game-10-home-score").textContent).toBe("0");
    expect(screen.getByTestId("game-10-away-score").textContent).toBe("7");
    expect(screen.getAllByTestId("game-10-total-row")).toHaveLength(1);
    expect(screen.getAllByTestId("game-10-total-value")).toHaveLength(1);
    expect(selected.closest("a")).toBeNull();
    expect(getComputedStyle(selected).gridTemplateColumns).toBe("repeat(2, minmax(0, 1fr))");
    for (const [sideName, team] of [["home", "Buffalo Bills"], ["away", "Miami Dolphins"]]) {
      const row = screen.getByTestId(`game-10-${sideName}-team-row`);
      const badge = within(row).getByTestId("team-abbreviation-badge");
      expect(badge.textContent).toBe(team === "Buffalo Bills" ? "BUF" : "MIA");
      expect(getComputedStyle(badge).fontFamily).toBe("var(--gk-font-mono)");
    }
  });

  it("reports unique upcoming matchups and actual model versions rather than pick count", () => {
    renderDashboard();
    expect(screen.getByTestId("upcoming-matchup-count").textContent).toBe("2");
    expect(screen.getByTestId("reported-model-version").textContent).toBe("NPI-4.0");
    expect(screen.getByRole("heading", { name: "Model Outcomes" })).toBeTruthy();
    expect(screen.getAllByRole("link", { name: /Read spread reasoning/ }).length).toBeGreaterThan(0);
  });

  it("keeps a long moneyline in Moneyline Value instead of Best Bet", () => {
    renderDashboard();

    expect(within(screen.getByTestId("daily-card-best-bet")).queryByText("Akron ML")).toBeNull();
    const moneyline = screen.getByTestId("daily-card-top-moneyline");
    expect(within(moneyline).getByText("Akron ML")).toBeTruthy();
    expect(moneyline.textContent).toContain("Odds +1300");
  });

  it("keeps a heavy favorite informational without recommending it", () => {
    renderDashboard();

    const gamesBoard = screen.getByTestId("sportsbook-games-board");
    expect(within(gamesBoard).getAllByText("-1000").length).toBeGreaterThan(0);
    expect(
      screen.getAllByTestId("game-10-moneyline-value").every(
        (cell) => cell.dataset.recommended === "false",
      ),
    ).toBe(true);
    for (const recommendation of [
      screen.getByTestId("daily-card-best-bet"),
      ...screen.getAllByTestId(/^daily-card-(top|next|value)/),
    ]) {
      expect(within(recommendation).queryByText("Buffalo Bills ML")).toBeNull();
    }
  });

  it("shows ranking reasons and requeries when sport changes", () => {
    renderDashboard();
    const bestBet = screen.getByTestId("daily-card-best-bet");
    expect(within(bestBet).getByText("NPI 188.0")).toBeTruthy();
    expect(within(bestBet).getByText("91.0 Confidence Rating")).toBeTruthy();
    expect(within(bestBet).queryByText(/projected edge/i)).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "NFL" }));
    expect(vi.mocked(useQuery).mock.calls.some(([options]) =>
      JSON.stringify(options.queryKey) === JSON.stringify(["product", "daily-card", "NFL"]),
    )).toBe(true);
    expect(vi.mocked(useQuery).mock.calls.some(([options]) =>
      JSON.stringify(options.queryKey) === JSON.stringify(["product", "predictions", "upcoming", "NFL"]),
    )).toBe(true);
  });

  it("offers accessible metric education without changing recommendation values", async () => {
    renderDashboard();

    expect(screen.getAllByRole("button", { name: "Learn about NPI" }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("button", { name: "Learn about Confidence Rating" }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("button", { name: "Learn about Model Probability" }).length).toBeGreaterThan(0);
    expect(screen.queryByRole("button", { name: "Learn about Projected Edge" })).toBeNull();
    expect(screen.getByText("Georgia -6.5")).toBeTruthy();
    expect(screen.queryByText(/projected edge/i)).toBeNull();
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
    mockQueries(undefined, gamePredictions, true);
    renderDashboard();

    expect(screen.getByText("Unable to load today's card right now.")).toBeTruthy();
    expect(screen.getByTestId("sportsbook-games-board")).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Model Outcomes" })).toBeTruthy();
  });

  it.each(["loading", "error"] as const)("keeps the card and outcomes available while upcoming games are %s", (state) => {
    const original = vi.mocked(useQuery).getMockImplementation()!;
    vi.mocked(useQuery).mockImplementation((options) =>
      options.queryKey[1] === "predictions"
        ? { data: undefined, isLoading: state === "loading", isError: state === "error", refetch: vi.fn() } as ReturnType<typeof useQuery>
        : original(options),
    );
    renderDashboard();
    expect(screen.getByTestId("daily-card-best-bet")).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Model Outcomes" })).toBeTruthy();
    expect(screen.getByTestId("upcoming-matchup-count").textContent).toBe("Unavailable");
    expect(screen.getByTestId("reported-model-version").textContent).toBe("Unavailable");
    expect(screen.getByText(state === "loading" ? "Loading upcoming matchups..." : "Unable to load upcoming matchups.")).toBeTruthy();
  });

  it("keeps the board and outcomes available while the daily card is loading", () => {
    const original = vi.mocked(useQuery).getMockImplementation()!;
    vi.mocked(useQuery).mockImplementation((options) =>
      options.queryKey[1] === "daily-card"
        ? { isLoading: true, data: undefined, isError: false } as ReturnType<typeof useQuery>
        : original(options),
    );
    renderDashboard();
    expect(screen.getByText("Building today's card...")).toBeTruthy();
    expect(screen.getByTestId("sportsbook-games-board")).toBeTruthy();
    expect(screen.getByTestId("upcoming-matchup-count").textContent).toBe("2");
    expect(screen.getByRole("heading", { name: "Model Outcomes" })).toBeTruthy();
  });
});
