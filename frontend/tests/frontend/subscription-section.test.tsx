import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { SubscriptionSection } from "../../src/components/SubscriptionSection";
import { ThemeModeProvider } from "../../src/theme/ThemeModeProvider";
import * as subscriptionService from "../../src/services/subscriptionService";

vi.mock("../../src/services/subscriptionService", async (importOriginal) => {
  const original = await importOriginal<typeof import("../../src/services/subscriptionService")>();
  return {
    ...original,
    getSubscription: vi.fn(),
    getPlans: vi.fn(),
    createCheckoutSession: vi.fn(),
    createBillingPortalSession: vi.fn(),
    redirectToExternal: vi.fn(),
  };
});

const freeSubscription: subscriptionService.SubscriptionOverview = {
  entitlement_key: "premium",
  plan: "free",
  status: "inactive",
  active: false,
  starts_at: null,
  ends_at: null,
  provider_subscriptions: [],
};

function renderSection(route = "/profile") {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <ThemeModeProvider>
        <MemoryRouter initialEntries={[route]}>
          <SubscriptionSection />
        </MemoryRouter>
      </ThemeModeProvider>
    </QueryClientProvider>,
  );
}

describe("subscription section", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(subscriptionService.getSubscription).mockResolvedValue(freeSubscription);
    vi.mocked(subscriptionService.getPlans).mockResolvedValue({
      currency: "USD", trial_days: 7,
      plans: [
        { id: "pro_monthly", name: "Bear A Hand Pro Monthly", amount_minor: 999, interval: "month" },
        { id: "pro_annual", name: "Bear A Hand Pro Annual", amount_minor: 8999, interval: "year" },
      ], premium_benefits: ["Full picks"],
    });
  });

  it.each([
    ["Monthly", "pro_monthly"],
    ["Annual", "pro_annual"],
  ] as const)("starts %s checkout and redirects to the server URL", async (label, plan) => {
    vi.mocked(subscriptionService.createCheckoutSession).mockResolvedValue({
      url: `https://checkout.stripe.test/${plan}`,
    });
    renderSection();

    fireEvent.click(await screen.findByRole("button", { name: `Choose ${label}` }));

    await waitFor(() => expect(subscriptionService.createCheckoutSession).toHaveBeenCalledWith(plan));
    expect(subscriptionService.redirectToExternal).toHaveBeenCalledWith(
      `https://checkout.stripe.test/${plan}`,
    );
  });

  it("disables both purchase buttons while checkout is pending", async () => {
    vi.mocked(subscriptionService.createCheckoutSession).mockReturnValue(new Promise(() => undefined));
    renderSection();

    fireEvent.click(await screen.findByRole("button", { name: "Choose Monthly" }));

    expect((await screen.findByRole("button", { name: "Opening checkout..." }) as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByRole("button", { name: "Choose Annual" }) as HTMLButtonElement).disabled).toBe(true);
  });

  it("refreshes canonical state after success without granting premium locally", async () => {
    renderSection("/profile?checkout=success&session_id=cs_test_context_only");

    expect(await screen.findByText(/Processing subscription access/i)).toBeTruthy();
    await waitFor(() => expect(subscriptionService.getSubscription).toHaveBeenCalled());
    expect(await screen.findByText("Free Preview access")).toBeTruthy();
    expect(screen.queryByText("Premium active")).toBeNull();
  });

  it("shows checkout cancellation without changing entitlement", async () => {
    renderSection("/profile?checkout=canceled");
    expect(await screen.findByText(/Checkout was canceled/i)).toBeTruthy();
    expect(await screen.findByText("Free Preview access")).toBeTruthy();
  });

  it.each([
    ["pro_monthly", "Bear A Hand Pro Monthly"],
    ["pro_annual", "Bear A Hand Pro Annual"],
  ] as const)("renders canonical premium plan %s", async (plan, label) => {
    vi.mocked(subscriptionService.getSubscription).mockResolvedValue({
      ...freeSubscription,
      plan,
      status: "active",
      active: true,
    });
    renderSection();
    expect(await screen.findByText("Premium active")).toBeTruthy();
    expect(screen.getAllByText(label).length).toBeGreaterThan(0);
  });

  it("opens billing management for a Stripe subscription", async () => {
    vi.mocked(subscriptionService.getSubscription).mockResolvedValue({
      ...freeSubscription,
      plan: "pro_monthly",
      status: "active",
      active: true,
      provider_subscriptions: [{
        provider: "stripe",
        plan: "pro_monthly",
        status: "active",
        current_period_end: null,
        trial_end: null,
        cancel_at_period_end: false,
      }],
    });
    vi.mocked(subscriptionService.createBillingPortalSession).mockResolvedValue({
      url: "https://billing.stripe.test/session",
    });
    renderSection();

    fireEvent.click(await screen.findByRole("button", { name: "Manage Billing" }));
    await waitFor(() => expect(subscriptionService.createBillingPortalSession).toHaveBeenCalled());
    expect(subscriptionService.redirectToExternal).toHaveBeenCalledWith(
      "https://billing.stripe.test/session",
    );
  });

  it.each(["active", "trialing"])("disables both plans for %s Premium while keeping billing available", async (status) => {
    vi.mocked(subscriptionService.getSubscription).mockResolvedValue({
      ...freeSubscription, plan: "pro_monthly", status: "active", active: true,
      provider_subscriptions: [{
        provider: "stripe", plan: "pro_monthly", status,
        current_period_end: null, trial_end: null, cancel_at_period_end: false,
      }],
    });
    renderSection();
    expect(await screen.findByText(/Premium access is already active/)).toBeTruthy();
    for (const label of ["Monthly", "Annual"]) {
      const button = screen.getByRole("button", { name: `Choose ${label}` });
      expect((button as HTMLButtonElement).disabled).toBe(true);
      fireEvent.click(button);
    }
    expect(subscriptionService.createCheckoutSession).not.toHaveBeenCalled();
    expect((screen.getByRole("button", { name: "Manage Billing" }) as HTMLButtonElement).disabled).toBe(false);
  });

  it("disables plan checkout until canonical access has loaded", async () => {
    vi.mocked(subscriptionService.getSubscription).mockReturnValue(new Promise(() => undefined));
    renderSection();
    expect((await screen.findByRole("button", { name: "Choose Monthly" }) as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByRole("button", { name: "Choose Annual" }) as HTMLButtonElement).disabled).toBe(true);
  });

  it("disables checkout when canonical access cannot be verified", async () => {
    vi.mocked(subscriptionService.getSubscription).mockRejectedValue(new Error("Offline"));
    renderSection();
    expect(await screen.findByText(/Unable to load subscription status/)).toBeTruthy();
    expect((screen.getByRole("button", { name: "Choose Monthly" }) as HTMLButtonElement).disabled).toBe(true);
    expect((screen.getByRole("button", { name: "Choose Annual" }) as HTMLButtonElement).disabled).toBe(true);
    expect(subscriptionService.createCheckoutSession).not.toHaveBeenCalled();
  });

  it("disables billing management while the portal request is pending", async () => {
    vi.mocked(subscriptionService.getSubscription).mockResolvedValue({
      ...freeSubscription,
      provider_subscriptions: [{
        provider: "stripe",
        plan: "pro_monthly",
        status: "active",
        current_period_end: null,
        trial_end: null,
        cancel_at_period_end: false,
      }],
    });
    vi.mocked(subscriptionService.createBillingPortalSession).mockReturnValue(
      new Promise(() => undefined),
    );
    renderSection();

    fireEvent.click(await screen.findByRole("button", { name: "Manage Billing" }));

    const pendingButton = await screen.findByRole("button", { name: "Opening billing..." });
    expect((pendingButton as HTMLButtonElement).disabled).toBe(true);
  });

  it("shows a safe inline checkout error", async () => {
    vi.mocked(subscriptionService.createCheckoutSession).mockRejectedValue(new Error("provider detail"));
    renderSection();
    fireEvent.click(await screen.findByRole("button", { name: "Choose Monthly" }));
    expect(await screen.findByText("Unable to start checkout. Please try again.")).toBeTruthy();
    expect(screen.queryByText("provider detail")).toBeNull();
  });

  it("displays authoritative prices and renewal/trial terms", async () => {
    renderSection();
    expect(await screen.findByText("$9.99 / month")).toBeTruthy();
    expect(screen.getByText("$89.99 / year")).toBeTruthy();
    expect(screen.getByText("Save about 25% with annual billing.")).toBeTruthy();
    expect(screen.getByText(/7-day trial.*renews automatically/)).toBeTruthy();
    expect(screen.getByText(/sandbox validation/)).toBeTruthy();
  });

  it("disables purchase when plan configuration cannot be loaded", async () => {
    vi.mocked(subscriptionService.getPlans).mockRejectedValue(new Error("Offline"));
    renderSection();
    expect(await screen.findByText(/Unable to load plans/)).toBeTruthy();
    expect(screen.queryByRole("button", { name: "Choose Monthly" })).toBeNull();
    expect(screen.getByRole("button", { name: "Refresh access" })).toBeTruthy();
  });

  it("bounds checkout polling and supports recovery without granting access", async () => {
    vi.useFakeTimers();
    try {
      renderSection("/profile?checkout=success");
      for (let index = 0; index < 25; index++) {
        await act(async () => { await vi.advanceTimersByTimeAsync(2000); });
      }
      expect(screen.getByText(/Access is not confirmed yet/)).toBeTruthy();
      const calls = vi.mocked(subscriptionService.getSubscription).mock.calls.length;
      await act(async () => { await vi.advanceTimersByTimeAsync(20000); });
      expect(subscriptionService.getSubscription).toHaveBeenCalledTimes(calls);
      expect(screen.queryByText("Premium active")).toBeNull();
      fireEvent.click(screen.getByRole("button", { name: "Refresh access" }));
      await act(async () => { await vi.advanceTimersByTimeAsync(1); });
      expect(subscriptionService.getSubscription).toHaveBeenCalledTimes(calls + 1);
    } finally { vi.useRealTimers(); }
  });

  it("stops polling when canonical Premium becomes active", async () => {
    vi.useFakeTimers();
    vi.mocked(subscriptionService.getSubscription).mockResolvedValueOnce(freeSubscription).mockResolvedValue({ ...freeSubscription, active: true });
    try {
      renderSection("/profile?checkout=success");
      for (let index = 0; index < 5; index++) {
        await act(async () => { await vi.advanceTimersByTimeAsync(2000); });
      }
      expect(screen.getByText("Premium access confirmed.")).toBeTruthy();
      const calls = vi.mocked(subscriptionService.getSubscription).mock.calls.length;
      await act(async () => { await vi.advanceTimersByTimeAsync(20000); });
      expect(subscriptionService.getSubscription).toHaveBeenCalledTimes(calls);
    } finally { vi.useRealTimers(); }
  });
});