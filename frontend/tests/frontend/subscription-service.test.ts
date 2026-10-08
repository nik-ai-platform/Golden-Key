import { beforeEach, describe, expect, it, vi } from "vitest";

import { client } from "../../src/api/client";
import {
  createBillingPortalSession,
  createCheckoutSession,
  getSubscription,
  getPlans,
  formatPlanPrice,
  annualSavingsLabel,
} from "../../src/services/subscriptionService";

vi.mock("../../src/api/client", () => ({
  client: {
    get: vi.fn(),
    post: vi.fn(),
  },
}));

describe("subscription service", () => {
  beforeEach(() => vi.clearAllMocks());
  it("fetches public pricing rather than creating client-owned prices", async () => {
    vi.mocked(client.get).mockResolvedValue({ data: { currency: "USD", plans: [] } });
    await getPlans();
    expect(client.get).toHaveBeenCalledWith("/subscriptions/plans");
    expect(formatPlanPrice(999, "USD")).toBe("$9.99");
    expect(formatPlanPrice(8999, "USD")).toBe("$89.99");
  });

  it("derives rounded annual savings from server amounts without an exact free-month claim", () => {
    const plans = [
      { id: "pro_monthly" as const, name: "Monthly", amount_minor: 999, interval: "month" as const },
      { id: "pro_annual" as const, name: "Annual", amount_minor: 8999, interval: "year" as const },
    ];
    expect(annualSavingsLabel(plans)).toBe("Save about 25% with annual billing.");
    expect(annualSavingsLabel(plans.slice(1))).toBeNull();
    expect(annualSavingsLabel([plans[0], { ...plans[1], amount_minor: 11988 }])).toBeNull();
    expect(annualSavingsLabel([{ ...plans[0], amount_minor: 0 }, plans[1]])).toBeNull();
  });

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