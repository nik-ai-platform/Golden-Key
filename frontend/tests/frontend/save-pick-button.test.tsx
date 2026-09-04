import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { SavePickButton } from "../../src/components/SavePickButton";
import { getSavedPicks, savePrediction } from "../../src/services/productApi";

vi.mock("../../src/services/productApi", () => ({
  getSavedPicks: vi.fn(),
  savePrediction: vi.fn(),
}));

function renderButton(predictionId = 42) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <SavePickButton predictionId={predictionId} />
    </QueryClientProvider>,
  );
}

describe("SavePickButton", () => {
  beforeEach(() => vi.clearAllMocks());

  it("shows Saved from a fresh server-saved state", async () => {
    vi.mocked(getSavedPicks).mockResolvedValue({
      count: 1,
      picks: [{ prediction_id: 42 }],
    } as Awaited<ReturnType<typeof getSavedPicks>>);

    renderButton();

    const button = await screen.findByRole("button", { name: "Saved" });
    expect((button as HTMLButtonElement).disabled).toBe(true);
  });

  it("shows an enabled Save Pick from a fresh unsaved state", async () => {
    vi.mocked(getSavedPicks).mockResolvedValue({ count: 0, picks: [] });

    renderButton();

    await waitFor(() => expect(getSavedPicks).toHaveBeenCalledTimes(1));
    const button = screen.getByRole("button", { name: "Save Pick" });
    expect((button as HTMLButtonElement).disabled).toBe(false);
  });

  it("transitions to Saved after the existing save call succeeds", async () => {
    vi.mocked(getSavedPicks).mockResolvedValue({ count: 0, picks: [] });
    vi.mocked(savePrediction).mockResolvedValue(undefined);

    renderButton(57);

    const saveButton = await screen.findByRole("button", { name: "Save Pick" });
    await waitFor(() => expect(getSavedPicks).toHaveBeenCalledTimes(1));
    fireEvent.click(saveButton);

    await waitFor(() => expect(savePrediction).toHaveBeenCalledWith(57));
    const savedButton = await screen.findByRole("button", { name: "Saved" });
    expect((savedButton as HTMLButtonElement).disabled).toBe(true);
  });
});