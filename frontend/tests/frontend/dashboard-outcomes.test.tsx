import { fireEvent, render, screen } from "@testing-library/react";
import { useQuery } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { DashboardOutcomes } from "../../src/components/DashboardOutcomes";
import { getPerformance } from "../../src/services/productApi";

vi.mock("@tanstack/react-query", () => ({ useQuery: vi.fn() }));

function show(result: object) {
  vi.mocked(useQuery).mockReturnValue(result as ReturnType<typeof useQuery>);
  return render(<MemoryRouter><DashboardOutcomes /></MemoryRouter>);
}

describe("dashboard outcomes", () => {
  it("uses the actual performance API, counts and recent results", () => {
    show({ data: { wins: 17, losses: 9, pushes: 3, recent_results: [{
      prediction_id: 1, game_id: 20, sport: "NFL", market: "spread", outcome: "LOSS",
      display_selection: "Home -3.5", away_team: "Away", home_team: "Home",
    }] }, isLoading: false, isError: false });
    expect(vi.mocked(useQuery).mock.calls.at(-1)?.[0]).toMatchObject({
      queryKey: ["product", "performance"], queryFn: getPerformance,
    });
    for (const count of ["17", "9", "3"]) expect(screen.getByText(count)).toBeTruthy();
    expect(screen.getByText("LOSS")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Home -3.5" }).getAttribute("href")).toBe("/games/20");
    expect(screen.getByRole("link", { name: "View all results" }).getAttribute("href")).toBe("/performance");
  });

  it("shows only the latest five API-ordered settled picks with their outcomes", () => {
    const outcomes = ["WIN", "LOSS", "PUSH", "WIN", "LOSS", "PUSH"];
    show({ data: { wins: 17, losses: 9, pushes: 3, recent_results: outcomes.map((outcome, index) => ({
      prediction_id: index + 1, game_id: index + 20, sport: "NCAAF", market: "total", outcome,
      display_selection: `Selection ${index + 1}`, away_team: "Long Away University", home_team: "Long Home University",
    })) } });
    const rows = screen.getAllByTestId("dashboard-recent-result");
    expect(rows).toHaveLength(5);
    expect(rows.map((row) => row.textContent)).toEqual(outcomes.slice(0, 5).map((outcome, index) =>
      `NCAAF · total${outcome}Selection ${index + 1}Long Away University @ Long Home University`,
    ));
    expect(screen.queryByText("Selection 6")).toBeNull();
  });

  it("shows loading without invented results", () => {
    show({ isLoading: true });
    expect(screen.getByText("Loading model outcomes...")).toBeTruthy();
    expect(screen.queryByText("Wins")).toBeNull();
  });

  it("shows errors and an explicit retry", () => {
    const refetch = vi.fn();
    show({ isError: true, isLoading: false, refetch });
    expect(screen.getByText("Unable to load model outcomes.")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /retry|try again/i }));
    expect(refetch).toHaveBeenCalledOnce();
  });

  it("reports a genuinely empty record", () => {
    show({ data: { wins: 0, losses: 0, pushes: 0, recent_results: [] } });
    expect(screen.getByText("No recent settled picks.")).toBeTruthy();
    expect(screen.queryByText("WIN")).toBeNull();
  });
});
