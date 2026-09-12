import { beforeEach, describe, expect, it, vi } from "vitest";

import { client } from "../../src/api/client";
import {
  createBillingPortalSession,
  createCheckoutSession,
  getSubscription,
} from "../../src/services/subscriptionService";

vi.mock("../../src/api/client", () => ({
  client: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe("subscription service", () => {
  beforeEach(() => vi.clearAllMocks());

  it("loads canonical subscription state", async () => {
    vi.mocked(client.get).mockResolvedValue({ data: { active: false } });
    await getSubscription();
    expect(client.get).toHaveBeenCalledWith("/subscriptions/me");
  });

  it.each(["pro_monthly", "pro_annual"] as const)(
    "creates a checkout session for %s without a client price ID",
    async (plan) => {
      vi.mocked(client.post).mockResolvedValue({ data: { url: "https://checkout.stripe.test" } });
      await createCheckoutSession(plan);
      expect(client.post).toHaveBeenCalledWith("/subscriptions/checkout-session", { plan });
      expect(client.post).not.toHaveBeenCalledWith(
        "/subscriptions/checkout-session",
        expect.objectContaining({ price_id: expect.anything() }),
      );
    },
  );

  it("creates a billing portal session", async () => {
    vi.mocked(client.post).mockResolvedValue({ data: { url: "https://billing.stripe.test" } });
    await createBillingPortalSession();
    expect(client.post).toHaveBeenCalledWith("/subscriptions/billing-portal");
  });
});