import { render, screen } from "@testing-library/react";
import { useQuery } from "@tanstack/react-query";
import { vi } from "vitest";

import { ProductSavedPicksPage } from "../../src/pages/ProductSavedPicksPage";

vi.mock("@tanstack/react-query", () => ({
  useQuery: vi.fn(),
}));

vi.mock("react-router-dom", () => ({
  useNavigate: () => vi.fn(),
}));

test("renders authoritative matchup and saved market details", () => {
  vi.mocked(useQuery).mockReturnValue({
    data: {
      count: 1,
      picks: [
        {
          saved_pick_id: 1,
          prediction_id: 11,
          game_id: 1,
          sport: "NFL",
          game_date: "2026-09-10T00:15:00Z",
          home_team: "Seattle Seahawks",
          away_team: "New England Patriots",
          matchup: "New England Patriots @ Seattle Seahawks",
          market: "spread",
          selection: "Seattle Seahawks",
          display_selection: "Seattle Seahawks -3.5",
          line_value: -3.5,
          american_odds: -110,
          npi_score: 142,
          confidence_score: 78,
          outcome: null,
        },
      ],
    },
    isLoading: false,
    isError: false,
  } as ReturnType<typeof useQuery>);

  render(<ProductSavedPicksPage />);

  expect(
    screen.getByText("New England Patriots @ Seattle Seahawks"),
  ).toBeTruthy();
  expect(screen.queryByText("Game #1")).toBeNull();
  expect(screen.getByText("Spread")).toBeTruthy();
  expect(screen.getByText("Seattle Seahawks -3.5")).toBeTruthy();
  expect(screen.getByText("NFL")).toBeTruthy();
  expect(screen.getByText("142")).toBeTruthy();
  expect(screen.getByText("78.0%")).toBeTruthy();
});