import { fireEvent, render, screen, waitFor } from "@testing-library/react";
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

    expect(await screen.findByText(/payment was completed/i)).toBeTruthy();
    await waitFor(() => expect(subscriptionService.getSubscription).toHaveBeenCalled());
    expect(await screen.findByText("Standard access")).toBeTruthy();
    expect(screen.queryByText("Premium active")).toBeNull();
  });

  it("shows checkout cancellation without changing entitlement", async () => {
    renderSection("/profile?checkout=canceled");
    expect(await screen.findByText(/Checkout was canceled/i)).toBeTruthy();
    expect(await screen.findByText("Standard access")).toBeTruthy();
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
});