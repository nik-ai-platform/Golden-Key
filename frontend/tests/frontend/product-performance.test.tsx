import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ProductPerformancePage } from "../../src/pages/ProductPerformancePage";
import { getPerformanceIntelligence } from "../../src/services/productApi";
import type {
  PerformanceIntelligenceBreakdown,
  PerformanceIntelligenceResponse,
} from "../../src/types/product";

vi.mock("../../src/services/productApi", () => ({
  getPerformanceIntelligence: vi.fn(),
}));

function breakdown(
  key: string,
  overrides: Partial<PerformanceIntelligenceBreakdown> = {},
): PerformanceIntelligenceBreakdown {
  return {
    key,
    total_bets: 2,
    wins: 1,
    losses: 1,
    pushes: 0,
    win_rate: 47.25,
    units_won: -1.2,
    roi: -4.3,
    ...overrides,
  };
}

const performance: PerformanceIntelligenceResponse = {
  period_days: 30,
  generated_at: "2026-09-02T00:52:25Z",
  overall: {
    total_bets: 6,
    wins: 3,
    losses: 2,
    pushes: 1,
    win_rate: 61.23,
    units_won: 3.42,
    roi: 8.55,
  },
  by_market: [breakdown("TOTAL"), breakdown("SPREAD"), breakdown("MONEYLINE")],
  by_sport: [breakdown("NBA"), breakdown("NFL"), breakdown("NCAAF")],
  by_npi_band: [breakdown("150-174")],
  by_confidence_band: [breakdown("80-89")],
  by_odds_band: [breakdown("+200 to +499")],
  by_side_type: [breakdown("Underdog"), breakdown("Favorite")],
  by_model_version: [breakdown("NPI-4.0")],
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
  return within(card as HTMLElement).getByRole("heading", { level: 5 }).textContent;
}

describe("Performance Intelligence", () => {
  beforeEach(() => {
    vi.mocked(getPerformanceIntelligence).mockResolvedValue(performance);
  });

  it("renders backend-provided overall metrics without recalculating them", async () => {
    renderPage();
    await screen.findByText("Total Bets");

    expect(summaryValue("Total Bets")).toBe("6");
    expect(summaryValue("Win Rate")).toBe("61.23%");
    expect(summaryValue("Units Won")).toBe("+3.42 units");
    expect(summaryValue("ROI")).toBe("+8.55%");
  });

  it("renders every backend breakdown in compact tables", async () => {
    renderPage();
    const market = await screen.findByRole("region", { name: "Market Performance" });
    const modelStrength = screen.getByRole("region", { name: "Model Strength" });
    const sport = screen.getByRole("region", { name: "Sport Performance" });
    const betProfile = screen.getByRole("region", { name: "Bet Profile" });
    const modelVersion = screen.getByRole("region", { name: "Model Version" });

    expect(within(market).getByText("Spread")).toBeTruthy();
    expect(within(market).getByText("Moneyline")).toBeTruthy();
    expect(within(market).getByText("Total")).toBeTruthy();
    expect(within(modelStrength).getByText("NPI Bands")).toBeTruthy();
    expect(within(modelStrength).getByText("150-174")).toBeTruthy();
    expect(within(modelStrength).getByText("80-89")).toBeTruthy();
    expect(within(modelStrength).getByText("+200 to +499")).toBeTruthy();
    expect(within(sport).getByText("NFL")).toBeTruthy();
    expect(within(sport).getByText("NCAAF")).toBeTruthy();
    expect(within(betProfile).getByText("Favorite")).toBeTruthy();
    expect(within(betProfile).getByText("Underdog")).toBeTruthy();
    expect(within(modelVersion).getByText("NPI-4.0")).toBeTruthy();
    expect(screen.getAllByText("-1.20 units").length).toBeGreaterThan(0);
    expect(screen.getAllByText("-4.30%").length).toBeGreaterThan(0);
  });

  it("refetches the backend when the selected period changes", async () => {
    renderPage();
    await waitFor(() => expect(getPerformanceIntelligence).toHaveBeenCalledWith(30));

    fireEvent.click(screen.getByRole("button", { name: "7 days" }));

    await waitFor(() => expect(getPerformanceIntelligence).toHaveBeenCalledWith(7));
  });

  it("shows loading, empty, and friendly error states", async () => {
    vi.mocked(getPerformanceIntelligence).mockImplementation(() => new Promise(() => undefined));
    const loading = renderPage();
    expect(screen.getByText("Loading performance intelligence...")).toBeTruthy();

    loading.unmount();
    vi.mocked(getPerformanceIntelligence).mockResolvedValue({
      ...performance,
      overall: {
        total_bets: 0,
        wins: 0,
        losses: 0,
        pushes: 0,
        win_rate: 0,
        units_won: 0,
        roi: 0,
      },
      by_market: [],
      by_sport: [],
      by_npi_band: [],
      by_confidence_band: [],
      by_odds_band: [],
      by_side_type: [],
      by_model_version: [],
    });
    const empty = renderPage();
    expect(await screen.findByText("No settled predictions in this period.")).toBeTruthy();
    expect(screen.queryByText("Market Performance")).toBeNull();

    empty.unmount();
    vi.mocked(getPerformanceIntelligence).mockRejectedValue(new Error("database detail"));
    renderPage();
    expect(
      await screen.findByText("Unable to load performance intelligence right now."),
    ).toBeTruthy();
    expect(screen.queryByText("database detail")).toBeNull();
  });
});