import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ProductSavedPicksPage } from "../../src/pages/ProductSavedPicksPage";
import { getSavedPicks, removeSavedPrediction } from "../../src/services/productApi";
import type { SavedPick, SavedPicksResponse } from "../../src/types/product";

vi.mock("../../src/services/productApi", () => ({
  getSavedPicks: vi.fn(),
  removeSavedPrediction: vi.fn(),
}));

function savedPick(overrides: Partial<SavedPick>): SavedPick {
  return {
    saved_pick_id: 1,
    prediction_id: 11,
    game_id: 101,
    sport: "NFL",
    game_date: "2026-09-10T00:15:00Z",
    home_team: "Seattle Seahawks",
    away_team: "New England Patriots",
    matchup: "New England Patriots @ Seattle Seahawks",
    market: "spread",
    selection: "HOME",
    display_selection: "Seattle Seahawks -3.5",
    line_value: -3.5,
    american_odds: -110,
    npi_score: 142,
    confidence_score: 78,
    risk_level: "LOW",
    outcome: null,
    home_score: null,
    away_score: null,
    ...overrides,
  };
}

const picks = [
  savedPick({
    saved_pick_id: 1,
    prediction_id: 11,
    game_id: 101,
    game_date: "2026-09-12T00:15:00Z",
  }),
  savedPick({
    saved_pick_id: 2,
    prediction_id: 12,
    game_id: 102,
    game_date: "2026-09-11T00:15:00Z",
    away_team: "Miami Dolphins",
    home_team: "Buffalo Bills",
    matchup: "Miami Dolphins @ Buffalo Bills",
    display_selection: "Miami Dolphins +2.5",
  }),
  savedPick({
    saved_pick_id: 3,
    prediction_id: 21,
    game_id: 201,
    game_date: "2026-09-08T00:15:00Z",
    away_team: "Dallas Cowboys",
    home_team: "Philadelphia Eagles",
    matchup: "Dallas Cowboys @ Philadelphia Eagles",
    market: "moneyline",
    selection: "AWAY",
    display_selection: "Dallas Cowboys ML",
    american_odds: 125,
    outcome: "WIN",
    away_score: 27,
    home_score: 20,
  }),
  savedPick({
    saved_pick_id: 4,
    prediction_id: 22,
    game_id: 202,
    game_date: "2026-09-09T00:15:00Z",
    away_team: "Chicago Bears",
    home_team: "Green Bay Packers",
    matchup: "Chicago Bears @ Green Bay Packers",
    outcome: "LOSS",
  }),
  savedPick({
    saved_pick_id: 5,
    prediction_id: 23,
    game_id: 203,
    game_date: "2026-09-07T00:15:00Z",
    away_team: "New York Jets",
    home_team: "Baltimore Ravens",
    matchup: "New York Jets @ Baltimore Ravens",
    market: "total",
    selection: "OVER",
    display_selection: "OVER 44.5",
    outcome: "PUSH",
  }),
];

function response(items: SavedPick[]): SavedPicksResponse {
  return { count: items.length, picks: items };
}

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/saved-picks"]}>
        <ProductSavedPicksPage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("saved picks tracking", () => {
  let serverData: SavedPicksResponse;

  beforeEach(() => {
    serverData = response(picks);
    vi.mocked(getSavedPicks).mockImplementation(async () => serverData);
    vi.mocked(removeSavedPrediction).mockImplementation(async (predictionId) => {
      serverData = response(
        serverData.picks.filter((pick) => pick.prediction_id !== predictionId),
      );
      return { removed: true, prediction_id: predictionId };
    });
  });

  it("separates authoritative outcomes and renders complete pick details", async () => {
    renderPage();

    expect((await screen.findByTestId("saved-count")).textContent).toBe("5");
    expect(screen.getByTestId("pending-count").textContent).toBe("2");
    expect(screen.getByTestId("settled-count").textContent).toBe("3");

    const pendingSection = screen.getByRole("region", { name: "Pending Picks" });
    const settledSection = screen.getByRole("region", { name: "Settled Picks" });
    expect(within(pendingSection).getAllByTestId("saved-pick-card")).toHaveLength(2);
    expect(within(settledSection).getAllByTestId("saved-pick-card")).toHaveLength(3);
    expect(within(pendingSection).queryByText(/^(WIN|LOSS|PUSH)$/)).toBeNull();
    for (const outcome of ["WIN", "LOSS", "PUSH"]) {
      expect(within(settledSection).getByText(outcome)).toBeTruthy();
    }

    expect(screen.getByText("Final: 27 - 20")).toBeTruthy();
    expect(screen.getAllByText("Seattle Seahawks -3.5")).toHaveLength(2);
    expect(screen.queryByText("HOME")).toBeNull();
    expect(screen.queryByText("AWAY")).toBeNull();
    expect(screen.getAllByText("142 / 200")).toHaveLength(5);
    expect(screen.getAllByText("78.0%")).toHaveLength(5);
    expect(within(pendingSection).getAllByText("LOW")).toHaveLength(2);

    const winCard = within(settledSection)
      .getByText("WIN")
      .closest("[data-testid='saved-pick-card']");
    expect(winCard).not.toBeNull();
    expect(
      within(winCard as HTMLElement)
        .getByRole("link", { name: /view game analysis/i })
        .getAttribute("href"),
    ).toBe("/games/201");
  });

  it("orders pending ascending and settled descending by game date", async () => {
    renderPage();
    await screen.findByTestId("saved-count");

    const pendingCards = within(
      screen.getByRole("region", { name: "Pending Picks" }),
    ).getAllByTestId("saved-pick-card");
    expect(pendingCards.map((card) => card.getAttribute("data-prediction-id"))).toEqual([
      "12",
      "11",
    ]);

    const settledCards = within(
      screen.getByRole("region", { name: "Settled Picks" }),
    ).getAllByTestId("saved-pick-card");
    expect(settledCards.map((card) => card.getAttribute("data-prediction-id"))).toEqual([
      "22",
      "21",
      "23",
    ]);
  });

  it.each([
    ["pending", 11],
    ["settled", 21],
  ])("removes a %s saved association through the existing behavior", async (_, predictionId) => {
    renderPage();
    await screen.findByTestId("saved-count");
    const card = screen
      .getAllByTestId("saved-pick-card")
      .find((item) => item.getAttribute("data-prediction-id") === String(predictionId));

    fireEvent.click(within(card as HTMLElement).getByRole("button", { name: /remove pick/i }));

    await waitFor(() => {
      expect(removeSavedPrediction).toHaveBeenCalledWith(predictionId);
      expect(
        screen
          .queryAllByTestId("saved-pick-card")
          .some((item) => item.getAttribute("data-prediction-id") === String(predictionId)),
      ).toBe(false);
    });
    expect(screen.queryByText(/delete result|delete history/i)).toBeNull();
  });

  it("shows loading and a friendly error without raw API details", async () => {
    vi.mocked(getSavedPicks).mockImplementation(() => new Promise(() => undefined));
    const view = renderPage();
    expect(screen.getByText("Loading saved picks...")).toBeTruthy();

    view.unmount();
    vi.mocked(getSavedPicks).mockRejectedValue(new Error("database detail"));
    renderPage();
    expect(await screen.findByText("Unable to load saved picks right now.")).toBeTruthy();
    expect(screen.queryByText("database detail")).toBeNull();
  });

  it("shows the full empty state", async () => {
    vi.mocked(getSavedPicks).mockResolvedValue(response([]));
    renderPage();

    expect(await screen.findByText("You have no saved picks yet.")).toBeTruthy();
    expect(screen.getByTestId("saved-count").textContent).toBe("0");
  });

  it.each([
    [picks.filter((pick) => pick.outcome), "No pending saved picks."],
    [picks.filter((pick) => !pick.outcome), "No settled saved picks yet."],
  ])("shows the appropriate partial empty state", async (items, message) => {
    vi.mocked(getSavedPicks).mockResolvedValue(response(items));
    renderPage();

    expect(await screen.findByText(message)).toBeTruthy();
  });

  it("keeps the card and hides raw removal errors when removal fails", async () => {
    vi.mocked(removeSavedPrediction).mockRejectedValue(new Error("database detail"));
    renderPage();

    const buttons = await screen.findAllByRole("button", { name: /remove pick/i });
    fireEvent.click(buttons[0]);

    expect(
      await screen.findByText(
        "Unable to remove this saved pick. Please try again.",
      ),
    ).toBeTruthy();
    expect(screen.getAllByTestId("saved-pick-card")).toHaveLength(5);
    expect(screen.queryByText("database detail")).toBeNull();
  });
});