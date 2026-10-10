import { fireEvent, render, screen, within } from "@testing-library/react";
import { useQuery } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ProductGameDetailPage } from "../../src/pages/ProductGameDetailPage";
import type { GameDetail, Prediction } from "../../src/types/product";
import { formatProductDate } from "../../src/utils/productFormat";

vi.mock("@tanstack/react-query", () => ({
  useQuery: vi.fn(),
}));

vi.mock("../../src/components/SavePickButton", () => ({
  SavePickButton: ({ predictionId }: { predictionId: number }) => (
    <button type="button">Save Pick {predictionId}</button>
  ),
}));

function prediction(overrides: Partial<Prediction>): Prediction {
  return {
    prediction_id: 1,
    game_id: 101,
    sport: "NFL",
    home_team: "Seattle Seahawks",
    away_team: "New England Patriots",
    game_date: "2026-09-10T00:15:00Z",
    market: "spread",
    selection: "HOME",
    display_selection: "Seattle Seahawks -3.5",
    line_value: -3.5,
    american_odds: -110,
    sportsbook: "DraftKings",
    odds_observed_at: "2026-09-01T20:32:00Z",
    model_version: "NPI-4.0",
    npi_score: 175,
    confidence_score: 83,
    simulation_probability: 61,
    projected_edge: 8.5,
    risk_level: "LOW",
    reasoning: "NPI Score: 175. Projected market edge: 8.5%. Seattle owns the stronger matchup profile.",
    outcome: "WIN",
    recommendation_eligible: true,
    recommendation_tier: null,
    recommendation_designation: null,
    ...overrides,
  };
}

const game: GameDetail = {
  game_id: 101,
  sport: "NFL",
  home_team: "Seattle Seahawks",
  away_team: "New England Patriots",
  game_date: "2026-09-10T00:15:00Z",
  home_score: 24,
  away_score: 21,
  predictions: [
    prediction({}),
    prediction({
      prediction_id: 2,
      market: "moneyline",
      selection: "AWAY",
      display_selection: "New England Patriots ML",
      american_odds: -1000,
      npi_score: 200,
      confidence_score: 95,
      projected_edge: 5,
      reasoning: null,
      outcome: "LOSS",
      recommendation_eligible: false,
      recommendation_tier: "LOW_VALUE_HEAVY_FAVORITE",
      recommendation_designation: "High Probability — Low Betting Value",
    }),
    prediction({
      prediction_id: 3,
      market: "total",
      selection: "OVER",
      display_selection: "OVER 44.5",
      line_value: 44.5,
      npi_score: 160,
      confidence_score: 74,
      projected_edge: 3.5,
      risk_level: null,
      reasoning: "Both offenses project above their recent baselines.",
      outcome: "PUSH",
    }),
  ],
};

function queryResult(options: {
  data?: GameDetail;
  isLoading?: boolean;
  isError?: boolean;
}) {
  return {
    data: options.data,
    isLoading: options.isLoading ?? false,
    isError: options.isError ?? false,
  } as ReturnType<typeof useQuery>;
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={["/games/101"]}>
      <Routes>
        <Route path="/games/:gameId" element={<ProductGameDetailPage />} />
      </Routes>
    </MemoryRouter>,
  );
}

describe("Game Analysis", () => {
  beforeEach(() => {
    vi.mocked(useQuery).mockReturnValue(queryResult({ data: game }));
  });

  it("retains informational historical picks with nullable metrics without crashing", () => {
    vi.mocked(useQuery).mockReturnValue(queryResult({
      data: {
        ...game,
        predictions: [prediction({
          npi_score: null, confidence_score: null, simulation_probability: null,
          projected_edge: null, line_value: null, american_odds: null, risk_level: null,
          recommendation_eligible: false, display_selection: "Seattle Seahawks",
        })],
      },
    }));
    renderPage();
    expect(screen.getAllByText("Unavailable").length).toBeGreaterThan(0);
    expect(screen.queryByText(/NaN|Infinity|null|undefined/)).toBeNull();
    expect(screen.queryByText(/American odds/)).toBeNull();
    expect(screen.getByRole("button", { name: "Save Pick 1" })).toBeTruthy();
  });

  it("renders the complete settled three-market decision view", () => {
    renderPage();

    expect(screen.getAllByText("New England Patriots @ Seattle Seahawks").length).toBeGreaterThan(0);
    expect(screen.getByText("NFL")).toBeTruthy();
    expect(screen.getByText(formatProductDate(game.game_date))).toBeTruthy();
    expect(screen.getByText("Final: New England Patriots 21 · Seattle Seahawks 24")).toBeTruthy();

    for (const label of ["Spread", "Moneyline", "Total"]) {
      expect(screen.getAllByText(label).length).toBeGreaterThan(0);
    }
    expect(screen.getByText("Seattle Seahawks -3.5")).toBeTruthy();
    expect(screen.getByText("New England Patriots ML")).toBeTruthy();
    expect(screen.getByText("OVER 44.5")).toBeTruthy();
    expect(screen.queryByText("HOME")).toBeNull();
    expect(screen.queryByText("AWAY")).toBeNull();
    expect(screen.getAllByText(/Quoted odds -110 · DraftKings/)).toHaveLength(2);
    expect(screen.getByText(/Quoted odds -1000 · DraftKings/)).toBeTruthy();
    expect(
      screen.getAllByText(new RegExp(
        `observed ${new Date("2026-09-01T20:32:00Z").toLocaleString()}`,
      )),
    ).toHaveLength(3);
    const spreadEducation = screen.getByRole("region", { name: "Understanding this spread pick" });
    const moneylineEducation = screen.getByRole("region", { name: "Understanding this moneyline pick" });
    const totalEducation = screen.getByRole("region", { name: "Understanding this total pick" });
    expect(screen.getAllByText("Understanding This Pick")).toHaveLength(3);
    expect(within(spreadEducation).getByText("175.0")).toBeTruthy();
    expect(within(spreadEducation).getByText("83.0")).toBeTruthy();
    expect(within(spreadEducation).getByText("61.0%")).toBeTruthy();
    expect(spreadEducation.textContent).toContain("New England Patriots @ Seattle Seahawks");
    expect(spreadEducation.textContent).toContain("Seattle Seahawks -3.5");
    expect(spreadEducation.textContent).toContain("Main uncertainty");
    expect(within(spreadEducation).queryByText("+8.5 pp")).toBeNull();
    expect(within(moneylineEducation).queryByText("+5.0 pp")).toBeNull();
    expect(within(totalEducation).queryByText("+3.5 pts")).toBeNull();
    expect(screen.getAllByTestId("pick-metrics")).toHaveLength(3);
    expect(screen.getAllByText("Confidence Rating")).toHaveLength(3);
    expect(screen.getAllByText("Model Probability")).toHaveLength(3);
    expect(spreadEducation.textContent).toContain("Seattle owns the stronger matchup profile.");
    expect(screen.getAllByRole("button", { name: "Learn about NPI" })).toHaveLength(3);
    expect(screen.getAllByText("Low")).toHaveLength(2);
    expect(screen.queryByText("LOW")).toBeNull();
    expect(screen.getAllByText("Bear A Hand Sports Best Pick")).toHaveLength(1);
    expect(screen.getByText("High Probability — Low Betting Value")).toBeTruthy();
    expect(screen.queryByText(/projected market edge/i)).toBeNull();
    expect(screen.getAllByText("Detailed breakdown unavailable for this pick.")).toHaveLength(3);
    expect(screen.getAllByRole("button", { name: /save pick/i })).toHaveLength(3);
    for (const outcome of ["WIN", "LOSS", "PUSH"]) {
      expect(screen.getByText(outcome)).toBeTruthy();
    }
    expect(screen.getByRole("link", { name: /back to games/i }).getAttribute("href")).toBe("/games");
  });

  it("shows only the historical model factor and frozen quote records for the exact pick", () => {
    vi.mocked(useQuery).mockReturnValue(queryResult({
      data: {
        ...game,
        home_score: null,
        away_score: null,
        predictions: [prediction({
          model_version: "NPI-5.0",
          selection: "AWAY",
          display_selection: "New England Patriots +3.5",
          line_value: 3.5,
          signal_breakdown: {
            model_version: "NPI-5.0",
            prediction_recorded_at: "2026-09-01T20:30:00Z",
            factors: [{
              factor_name: "Historical Rule Engine",
              weight: 80,
              factor_score: 20,
              predicted_side: "AWAY",
              recorded_at: "2026-09-01T20:30:01Z",
            }],
            frozen_odds: {
              snapshot_id: 9001,
              sportsbook: "DraftKings",
              spread_home: -3.5,
              spread_away: 3.5,
              spread_home_price: -110,
              spread_away_price: -110,
              moneyline_home: -165,
              moneyline_away: 145,
              total: 44.5,
              total_over_price: -110,
              total_under_price: -110,
              recorded_at: "2026-09-01T20:32:00Z",
            },
            recorded_explanation:
              "Spread model. Key Advantages: Recorded away-side rule. Risk Factors: No historical rule matched.",
          },
        })],
      },
    }));

    renderPage();
    fireEvent.click(screen.getByRole("button", { name: "View signal breakdown" }));

    expect(screen.getByText("Recorded model factors · NPI-5.0")).toBeTruthy();
    expect(screen.getByText("Historical Rule Engine")).toBeTruthy();
    expect(screen.getByText("20 / 80")).toBeTruthy();
    expect(screen.getByText(/Recorded side:\s*AWAY/)).toBeTruthy();
    expect(screen.getByText(/Recorded away-side rule/)).toBeTruthy();
    expect(screen.getByText(/Spread home\/away: -3\.5 \/ 3\.5/)).toBeTruthy();
    expect(screen.getByText(/Snapshot 9001 · DraftKings/)).toBeTruthy();
    expect(screen.queryByRole("progressbar")).toBeNull();
  });

  it("treats PASS as no selection and does not present stored text as a pick reason", () => {
    vi.mocked(useQuery).mockReturnValue(queryResult({
      data: {
        ...game,
        home_score: null,
        away_score: null,
        predictions: [prediction({
          selection: "PASS",
          display_selection: "PASS",
          reasoning: "PASS. No selection recommended.",
        })],
      },
    }));
    renderPage();

    const brief = screen.getByRole("region", { name: "Understanding this spread pick" });
    expect(within(brief).getByText("No selection recorded (PASS)")).toBeTruthy();
    expect(within(brief).getByText("No pick-specific supporting reasons were recorded.")).toBeTruthy();
    expect(within(brief).queryByText("No selection recommended.")).toBeNull();
  });

  it("omits a missing market safely", () => {
    vi.mocked(useQuery).mockReturnValue(
      queryResult({ data: { ...game, home_score: null, away_score: null, predictions: game.predictions.slice(0, 2) } }),
    );
    renderPage();

    expect(screen.getAllByText("Spread").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Moneyline").length).toBeGreaterThan(0);
    expect(screen.queryByText("Total")).toBeNull();
    expect(screen.queryByText(/^Final:/)).toBeNull();
  });

  it("shows loading and friendly unavailable states", () => {
    vi.mocked(useQuery).mockReturnValue(queryResult({ isLoading: true }));
    const view = renderPage();
    expect(screen.getByText("Loading game analysis...")).toBeTruthy();

    vi.mocked(useQuery).mockReturnValue(queryResult({ isError: true }));
    view.rerender(
      <MemoryRouter initialEntries={["/games/101"]}>
        <Routes>
          <Route path="/games/:gameId" element={<ProductGameDetailPage />} />
        </Routes>
      </MemoryRouter>,
    );
    expect(screen.getByText("Game analysis is unavailable.")).toBeTruthy();
  });

  it("keeps the matchup visible when no predictions exist", () => {
    vi.mocked(useQuery).mockReturnValue(
      queryResult({ data: { ...game, home_score: null, away_score: null, predictions: [] } }),
    );
    renderPage();

    expect(screen.getAllByText("New England Patriots @ Seattle Seahawks").length).toBeGreaterThan(0);
    expect(screen.getByText("No Bear A Hand Sports predictions are available for this game yet.")).toBeTruthy();
  });
});