import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AuthContext } from "../../src/auth/AuthContextDefinition";
import { PremiumRoute } from "../../src/components/PremiumRoute";
import { FreePreviewPage } from "../../src/pages/FreePreviewPage";
import { getSubscription } from "../../src/services/subscriptionService";
import { client } from "../../src/api/client";

vi.mock("../../src/services/subscriptionService", () => ({ getSubscription: vi.fn() }));
vi.mock("../../src/api/client", () => ({ client: { get: vi.fn() } }));
const free = { active: false, plan: "free", entitlement_key: "premium", status: "inactive", starts_at: null, ends_at: null, provider_subscriptions: [] };
function renderGate(role: "user" | "admin" | "analyst" | "viewer" = "user", preview = false) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(<QueryClientProvider client={queryClient}><AuthContext.Provider value={{
    user: { id: 1, username: "Customer", email: "customer@example.test", role, is_active: true },
    isAuthenticated: true, isBootstrapping: false, login: vi.fn(), logout: vi.fn(),
  }}><MemoryRouter><PremiumRoute preview={preview ? <FreePreviewPage /> : undefined}><h1>Full Premium picks</h1></PremiumRoute></MemoryRouter></AuthContext.Provider></QueryClientProvider>);
}
describe("canonical customer access", () => {
  beforeEach(() => { vi.clearAllMocks(); vi.mocked(getSubscription).mockResolvedValue(free); });
  it.each(["user", "analyst", "viewer"] as const)("denies inactive %s regardless of role", async (role) => {
    renderGate(role);
    expect(await screen.findByText("Premium feature")).toBeTruthy();
    expect(screen.queryByText("Full Premium picks")).toBeNull();
    expect(screen.getByRole("link", { name: "Explore Premium" }).getAttribute("href")).toBe("/profile");
  });
  it("shows no Premium content while loading", () => {
    vi.mocked(getSubscription).mockReturnValue(new Promise(() => undefined));
    renderGate();
    expect(screen.getByText("Checking Premium access...")).toBeTruthy();
    expect(screen.queryByText("Full Premium picks")).toBeNull();
  });
  it("fails closed on errors and supports accessible refresh", async () => {
    vi.mocked(getSubscription).mockRejectedValueOnce(new Error("Offline")).mockResolvedValueOnce({ ...free, active: true });
    renderGate();
    expect(await screen.findByText(/Unable to verify Premium access/)).toBeTruthy();
    expect(screen.queryByText("Full Premium picks")).toBeNull();
    fireEvent.click(screen.getByRole("button", { name: "Refresh access" }));
    expect(await screen.findByText("Full Premium picks")).toBeTruthy();
  });
  it("allows canonical active subscribers", async () => {
    vi.mocked(getSubscription).mockResolvedValue({ ...free, active: true });
    renderGate();
    expect(await screen.findByText("Full Premium picks")).toBeTruthy();
  });
  it("allows paid access pending period-end cancellation until canonical access expires", async () => {
    vi.mocked(getSubscription).mockResolvedValue({
      ...free, active: true, status: "active",
      provider_subscriptions: [{ provider: "stripe", plan: "pro_monthly", status: "active", current_period_end: "2026-11-01T00:00:00Z", trial_end: null, cancel_at_period_end: true }],
    });
    renderGate();
    expect(await screen.findByText("Full Premium picks")).toBeTruthy();
  });
  it("denies canceled canonical access", async () => {
    vi.mocked(getSubscription).mockResolvedValue({ ...free, status: "canceled", active: false });
    renderGate();
    expect(await screen.findByText("Premium feature")).toBeTruthy();
    expect(screen.queryByText("Full Premium picks")).toBeNull();
  });
  it("explicitly allows authenticated admins without a payment dependency", () => {
    renderGate("admin");
    expect(screen.getByText("Full Premium picks")).toBeTruthy();
    expect(getSubscription).not.toHaveBeenCalled();
  });
  it("fetches only the safe preview and ignores unexpected Premium fields", async () => {
    vi.mocked(client.get).mockResolvedValue({ data: { sport: null, count: 1, games: [{
      game_id: 1, sport: "NBA", league: "NBA", home_team: "Home", away_team: "Away",
      start_time: null, status: "scheduled", selection: "SECRET PICK", odds: -110,
    }] } });
    renderGate("user", true);
    expect(await screen.findByText("Away at Home")).toBeTruthy();
    expect(screen.queryByText("SECRET PICK")).toBeNull();
    expect(screen.queryByText(/-110/)).toBeNull();
    await waitFor(() => expect(client.get).toHaveBeenCalledWith("/product/preview"));
    expect(client.get).toHaveBeenCalledTimes(1);
  });
});
