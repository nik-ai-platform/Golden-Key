import { afterEach, describe, expect, it, vi } from "vitest";

import { client } from "../../src/api/client";
import { removeSavedPrediction } from "../../src/services/productApi";

describe("saved picks API", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("deletes the authenticated association by prediction_id", async () => {
    const response = { removed: true, prediction_id: 123 };
    const deleteMock = vi.spyOn(client, "delete").mockResolvedValue({
      data: response,
    });

    await expect(removeSavedPrediction(123)).resolves.toEqual(response);
    expect(deleteMock).toHaveBeenCalledWith(
      "/users/saved-predictions/123",
    );
  });
});