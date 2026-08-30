import { render, screen } from "@testing-library/react";
import { useQuery } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ProductGameDetailPage } from "../../src/pages/ProductGameDetailPage";
import type { GameDetail, Prediction } from "../../src/types/product";

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
    model_version: "NPI-4.0",
    npi_score: 175,
    confidence_score: 83,
    simulation_probability: 61,
    projected_edge: 8.5,
    risk_level: "LOW",
    reasoning: "Seattle owns the stronger matchup profile.",
    outcome: "WIN",
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
      american_odds: 125,
      npi_score: 168,
      confidence_score: 78,
      projected_edge: 5,
      reasoning: null,
      outcome: "LOSS",
    }),
    prediction({
      prediction_id: 3,
      market: "total",
      selection: "OVER",
      display_selection: "OVER 44.5",
      line_value: 44.5,
      npi_score: 160,
      confidence_score: 74,
      projected_edge: null,
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

  it("renders the complete settled three-market decision view", () => {
    renderPage();

    expect(screen.getByText("New England Patriots @ Seattle Seahawks")).toBeTruthy();
    expect(screen.getByText("NFL")).toBeTruthy();
    expect(
      screen.getByText(
        new Date(game.game_date).toLocaleString(undefined, {
          weekday: "long",
          month: "long",
          day: "numeric",
          year: "numeric",
          hour: "numeric",
          minute: "2-digit",
        }),
      ),
    ).toBeTruthy();
    expect(screen.getByText("Final: New England Patriots 21 · Seattle Seahawks 24")).toBeTruthy();

    for (const label of ["Spread", "Moneyline", "Total"]) {
      expect(screen.getByText(label)).toBeTruthy();
    }
    expect(screen.getByText("Seattle Seahawks -3.5")).toBeTruthy();
    expect(screen.getByText("New England Patriots ML")).toBeTruthy();
    expect(screen.getByText("OVER 44.5")).toBeTruthy();
    expect(screen.queryByText("HOME")).toBeNull();
    expect(screen.queryByText("AWAY")).toBeNull();
    expect(screen.getAllByText("American odds -110")).toHaveLength(2);
    expect(screen.getByText("American odds +125")).toBeTruthy();
    expect(screen.getAllByText("/ 200")).toHaveLength(3);
    expect(screen.getAllByText("Confidence")).toHaveLength(3);
    expect(screen.getByText("83%")).toBeTruthy();
    expect(screen.getAllByText("Golden Key Best Pick")).toHaveLength(1);
    expect(screen.getByText("Seattle owns the stronger matchup profile.")).toBeTruthy();
    expect(screen.getAllByText("Why Golden Key Likes This Pick")).toHaveLength(2);
    expect(screen.getAllByRole("button", { name: /save pick/i })).toHaveLength(3);
    for (const outcome of ["WIN", "LOSS", "PUSH"]) {
      expect(screen.getByText(outcome)).toBeTruthy();
    }
    expect(screen.getByRole("link", { name: /back to games/i }).getAttribute("href")).toBe("/games");
  });

  it("omits a missing market safely", () => {
    vi.mocked(useQuery).mockReturnValue(
      queryResult({ data: { ...game, home_score: null, away_score: null, predictions: game.predictions.slice(0, 2) } }),
    );
    renderPage();

    expect(screen.getByText("Spread")).toBeTruthy();
    expect(screen.getByText("Moneyline")).toBeTruthy();
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

    expect(screen.getByText("New England Patriots @ Seattle Seahawks")).toBeTruthy();
    expect(screen.getByText("No Golden Key predictions are available for this game yet.")).toBeTruthy();
  });
});