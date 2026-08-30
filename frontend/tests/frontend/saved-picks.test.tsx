import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ProductSavedPicksPage } from "../../src/pages/ProductSavedPicksPage";
import { getSavedPicks, removeSavedPrediction } from "../../src/services/productApi";
import type { SavedPick, SavedPicksResponse } from "../../src/types/product";

vi.mock("react-router-dom", () => ({
  useNavigate: () => vi.fn(),
}));

vi.mock("../../src/services/productApi", () => ({
  getSavedPicks: vi.fn(),
  removeSavedPrediction: vi.fn(),
}));

const savedPick: SavedPick = {
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
};

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <ProductSavedPicksPage />
    </QueryClientProvider>,
  );
}

describe("saved picks", () => {
  let serverData: SavedPicksResponse;

  beforeEach(() => {
    serverData = { count: 1, picks: [savedPick] };
    vi.mocked(getSavedPicks).mockImplementation(async () => serverData);
    vi.mocked(removeSavedPrediction).mockReset();
  });

  it("renders authoritative details and a Remove Pick control", async () => {
    renderPage();

    expect(await screen.findByText(savedPick.matchup)).toBeTruthy();
    expect(screen.queryByText("Game #1")).toBeNull();
    expect(screen.getByText("Spread")).toBeTruthy();
    expect(screen.getByText("Seattle Seahawks -3.5")).toBeTruthy();
    expect(screen.getByText("NFL")).toBeTruthy();
    expect(screen.getByText("142")).toBeTruthy();
    expect(screen.getByText("78.0%")).toBeTruthy();
    expect(screen.getByRole("button", { name: /remove pick/i })).toBeTruthy();
  });

  it("shows pending state, calls with prediction_id, and removes the final card", async () => {
    let resolveRemoval: (
      value: { removed: boolean; prediction_id: number },
    ) => void = () => undefined;
    vi.mocked(removeSavedPrediction).mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveRemoval = resolve;
        }),
    );
    renderPage();
    const button = await screen.findByRole("button", { name: /remove pick/i });

    fireEvent.click(button);

    const pendingButton = await screen.findByRole("button", {
      name: "Removing...",
    });
    expect(removeSavedPrediction).toHaveBeenCalledWith(11);
    expect((pendingButton as HTMLButtonElement).disabled).toBe(true);

    serverData = { count: 0, picks: [] };
    resolveRemoval({ removed: true, prediction_id: 11 });

    expect(await screen.findByText("No saved picks")).toBeTruthy();
    expect(screen.queryByText(savedPick.matchup)).toBeNull();
  });

  it("keeps the card and shows a friendly error when removal fails", async () => {
    vi.mocked(removeSavedPrediction).mockRejectedValue(new Error("database detail"));
    renderPage();

    fireEvent.click(await screen.findByRole("button", { name: /remove pick/i }));

    expect(
      await screen.findByText(
        "Unable to remove this saved pick. Please try again.",
      ),
    ).toBeTruthy();
    expect(screen.getByText(savedPick.matchup)).toBeTruthy();
    await waitFor(() =>
      expect(
        (screen.getByRole("button", {
          name: /remove pick/i,
        }) as HTMLButtonElement).disabled,
      ).toBe(false),
    );
    expect(screen.queryByText("database detail")).toBeNull();
  });
});