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
  npi_4_spread: {
    summary: {
      sample_size: 12,
      wins: 7,
      losses: 4,
      pushes: 1,
      win_rate: 63.64,
      units: 2.75,
      roi: 22.92,
    },
    npi_bands: [
      { key: "0-99", sample_size: 0, wins: 0, losses: 0, pushes: 0, win_rate: 0, units: 0, roi: 0 },
      { key: "150-174", sample_size: 4, wins: 3, losses: 1, pushes: 0, win_rate: 75, units: 1.73, roi: 43.25 },
    ],
    confidence_bands: [
      { key: "80-89", sample_size: 3, wins: 2, losses: 1, pushes: 0, win_rate: 66.67, units: 0.82, roi: 27.33 },
    ],
    projected_edge_bands: [
      { key: "10-14.9", sample_size: 5, wins: 3, losses: 2, pushes: 0, win_rate: 60, units: 0.73, roi: 14.6 },
    ],
    probability_calibration: [
      { key: "60-64.9", sample_size: 4, wins: 3, losses: 1, pushes: 0, predicted_probability_average: 62.5, actual_win_rate: 75 },
    ],
    brier_score: 0.2143,
    brier_sample_size: 11,
  },
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
  const card = within(screen.getByTestId("overall-metrics-grid"))
    .getByText(label, { selector: "p" })
    .closest(".MuiCard-root");
  return within(card as HTMLElement).getByRole("heading", { level: 5 }).textContent;
}

function spreadSummaryValue(label: string): string | null {
  const card = within(screen.getByTestId("npi-4-spread-summary"))
    .getByText(label, { selector: "p" })
    .closest(".MuiCard-root");
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

  it("renders NPI 4.0 actionable spread summary and Brier Score", async () => {
    renderPage();
    const section = await screen.findByRole("region", { name: "NPI 4.0 Spread Performance" });

    expect(within(section).getByText("Settled, actionable spread predictions generated by NPI 4.0.")).toBeTruthy();
    expect(spreadSummaryValue("ATS Record")).toBe("7-4-1");
    expect(spreadSummaryValue("ATS Win Rate")).toBe("63.64%");
    expect(spreadSummaryValue("Units")).toBe("+2.75 units");
    expect(spreadSummaryValue("ROI")).toBe("+22.92%");
    expect(spreadSummaryValue("Sample Size")).toBe("12");
    expect(spreadSummaryValue("Brier Score")).toBe("0.2143");
    expect(within(section).getByText("Measures probability accuracy. Lower is better.")).toBeTruthy();
  });

  it("renders NPI, confidence, and probability calibration tables", async () => {
    renderPage();
    const section = await screen.findByRole("region", { name: "NPI 4.0 Spread Performance" });

    expect(within(section).getByRole("table", { name: "NPI Performance table" })).toBeTruthy();
    expect(within(section).getByRole("table", { name: "Confidence Performance table" })).toBeTruthy();
    expect(within(section).queryByRole("table", { name: "Projected Edge Performance table" })).toBeNull();
    expect(within(section).getByRole("table", { name: "Model Probability Calibration table" })).toBeTruthy();
    expect(within(section).getByText("0-99")).toBeTruthy();
    expect(within(section).getByText("60-64.9")).toBeTruthy();
    expect(within(section).getByText("62.50%")).toBeTruthy();
  });

  it("contains wide tables within scrollable section wrappers", async () => {
    renderPage();
    await screen.findByText("Total Bets");

    const metricsStyle = getComputedStyle(screen.getByTestId("overall-metrics-grid"));
    expect(metricsStyle.display).toBe("grid");
    expect(metricsStyle.minWidth).toBe("0px");
    expect(metricsStyle.width).toBe("100%");
    for (const table of screen.getAllByRole("table")) {
      expect(getComputedStyle(table).minWidth).toBe("640px");
      expect(getComputedStyle(table.parentElement!).overflowX).toBe("auto");
      expect(getComputedStyle(table.parentElement!).width).toBe("100%");
    }
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
    expect(screen.getByText("NPI 4.0 Spread Performance")).toBeTruthy();
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