import { render, screen, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ProductPerformancePage } from "../../src/pages/ProductPerformancePage";
import { getPerformance } from "../../src/services/productApi";
import type {
  Performance,
  RecentPerformanceResult,
} from "../../src/types/product";

vi.mock("../../src/services/productApi", () => ({
  getPerformance: vi.fn(),
}));

function recentResult(
  overrides: Partial<RecentPerformanceResult>,
): RecentPerformanceResult {
  return {
    prediction_id: 1,
    game_id: 10,
    sport: "NFL",
    game_date: "2026-09-08T00:15:00Z",
    home_team: "Seattle Seahawks",
    away_team: "New England Patriots",
    market: "spread",
    display_selection: "Seattle Seahawks -3.5",
    npi_score: 142,
    outcome: "WIN",
    home_score: 24,
    away_score: 17,
    ...overrides,
  };
}

const performance: Performance = {
  total_predictions: 6,
  wins: 3,
  losses: 2,
  pushes: 1,
  accuracy: 60,
  profit_loss: 125.5,
  market_performance: [
    { name: "total", settled: 2, wins: 1, losses: 1, pushes: 0, win_rate: 50 },
    { name: "spread", settled: 2, wins: 1, losses: 1, pushes: 0, win_rate: 50 },
    { name: "moneyline", settled: 2, wins: 1, losses: 0, pushes: 1, win_rate: 100 },
  ],
  sport_performance: [
    { name: "NBA", settled: 3, wins: 1, losses: 1, pushes: 1, win_rate: 50 },
    { name: "NFL", settled: 3, wins: 2, losses: 1, pushes: 0, win_rate: 66.67 },
  ],
  recent_results: [
    recentResult({ prediction_id: 1, outcome: "WIN" }),
    recentResult({
      prediction_id: 2,
      game_date: "2026-09-10T00:15:00Z",
      away_team: "Dallas Cowboys",
      home_team: "Philadelphia Eagles",
      market: "moneyline",
      display_selection: "Dallas Cowboys ML",
      outcome: "LOSS",
      home_score: 27,
      away_score: 20,
    }),
    recentResult({
      prediction_id: 3,
      game_date: "2026-09-09T00:15:00Z",
      sport: "NBA",
      away_team: "New York Knicks",
      home_team: "Boston Celtics",
      market: "total",
      display_selection: "OVER 218.5",
      npi_score: 175,
      outcome: "PUSH",
      home_score: 109,
      away_score: 109,
    }),
  ],
};

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <ProductPerformancePage />
    </QueryClientProvider>,
  );
}

function summaryValue(label: string): string | null {
  const card = screen.getByText(label, { selector: "p" }).closest(".MuiCard-root");
  return within(card as HTMLElement).getByRole("heading", { level: 4 }).textContent;
}

describe("Performance results summary", () => {
  beforeEach(() => {
    vi.mocked(getPerformance).mockResolvedValue(performance);
  });

  it("renders settled totals and excludes pushes from the win-rate denominator", async () => {
    renderPage();
    await screen.findByRole("heading", { name: "Performance" });

    expect(summaryValue("Total Settled")).toBe("6");
    expect(summaryValue("Wins")).toBe("3");
    expect(summaryValue("Losses")).toBe("2");
    expect(summaryValue("Pushes")).toBe("1");
    expect(summaryValue("Win Rate")).toBe("60.0%");
    expect(screen.queryByText(/profit|roi|\$/i)).toBeNull();
  });

  it("renders populated market and sport breakdowns only", async () => {
    renderPage();
    const marketSection = await screen.findByRole("region", {
      name: "Market Performance",
    });
    const sportSection = screen.getByRole("region", { name: "Sport Performance" });

    for (const market of ["Spread", "Moneyline", "Total"]) {
      expect(within(marketSection).getByRole("heading", { name: market })).toBeTruthy();
    }
    expect(within(marketSection).getByText("1 W · 0 L · 1 P")).toBeTruthy();
    expect(within(sportSection).getByRole("heading", { name: "NFL" })).toBeTruthy();
    expect(within(sportSection).getByRole("heading", { name: "NBA" })).toBeTruthy();
    expect(
      within(sportSection).getByText(
        (_, element) => element?.tagName === "P" && element.textContent === "Record 2-1-0",
      ),
    ).toBeTruthy();
    expect(within(sportSection).queryByText("WNBA")).toBeNull();
  });

  it("renders authoritative recent results newest first", async () => {
    renderPage();
    const section = await screen.findByRole("region", { name: "Recent Results" });
    const rows = within(section).getAllByTestId("recent-result");

    expect(rows.map((row) => row.getAttribute("data-prediction-id"))).toEqual([
      "2",
      "3",
      "1",
    ]);
    expect(within(section).getByText("Dallas Cowboys ML")).toBeTruthy();
    expect(within(section).queryByText("HOME")).toBeNull();
    expect(within(section).queryByText("AWAY")).toBeNull();
    expect(within(section).getByText("NPI 175.0 / 200")).toBeTruthy();
    for (const outcome of ["WIN", "LOSS", "PUSH"]) {
      expect(within(section).getByText(outcome)).toBeTruthy();
    }
    expect(within(section).getByText("Final: 20 - 27")).toBeTruthy();
  });

  it("shows an em dash when settled results contain no decisions", async () => {
    vi.mocked(getPerformance).mockResolvedValue({
      ...performance,
      total_predictions: 2,
      wins: 0,
      losses: 0,
      pushes: 2,
      accuracy: 0,
    });
    renderPage();

    await screen.findByRole("heading", { name: "Performance" });
    expect(summaryValue("Win Rate")).toBe("—");
  });

  it("shows loading, empty, and friendly error states", async () => {
    vi.mocked(getPerformance).mockImplementation(() => new Promise(() => undefined));
    const loading = renderPage();
    expect(screen.getByText("Loading performance...")).toBeTruthy();

    loading.unmount();
    vi.mocked(getPerformance).mockResolvedValue({
      ...performance,
      total_predictions: 0,
      wins: 0,
      losses: 0,
      pushes: 0,
      market_performance: [],
      sport_performance: [],
      recent_results: [],
    });
    const empty = renderPage();
    expect(
      await screen.findByText("No settled Golden Key predictions are available yet."),
    ).toBeTruthy();
    expect(screen.queryByText("Market Performance")).toBeNull();

    empty.unmount();
    vi.mocked(getPerformance).mockRejectedValue(new Error("database detail"));
    renderPage();
    expect(await screen.findByText("Unable to load performance right now.")).toBeTruthy();
    expect(screen.queryByText("database detail")).toBeNull();
  });
});