import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { expect, it, vi } from "vitest";

import { SavePickButton } from "../../src/components/SavePickButton";

vi.mock("../../src/services/productApi", () => ({
  getSavedPicks: vi.fn(),
  savePrediction: vi.fn(),
}));

it("shows Saved when the prediction is already in the Saved Picks cache", () => {
  const queryClient = new QueryClient();
  queryClient.setQueryData(["product", "saved-picks"], {
    count: 1,
    picks: [{ prediction_id: 42 }],
  });

  render(
    <QueryClientProvider client={queryClient}>
      <SavePickButton predictionId={42} />
    </QueryClientProvider>,
  );

  const button = screen.getByRole("button", { name: "Saved" });
  expect((button as HTMLButtonElement).disabled).toBe(true);
});