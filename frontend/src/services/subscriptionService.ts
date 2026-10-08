import { client } from "../api/client";

export type SubscriptionPlan = "pro_monthly" | "pro_annual";
export interface ProductPlans {
  currency: string;
  trial_days: number;
  plans: { id: SubscriptionPlan; name: string; amount_minor: number; interval: "month" | "year" }[];
  premium_benefits: string[];
}

export async function getPlans(): Promise<ProductPlans> {
  const { data } = await client.get<ProductPlans>("/subscriptions/plans");
  return data;
}

export function formatPlanPrice(amountMinor: number, currency: string): string {
  return new Intl.NumberFormat(undefined, { style: "currency", currency }).format(amountMinor / 100);
}

export function annualSavingsLabel(plans: ProductPlans["plans"]): string | null {
  const monthly = plans.find((plan) => plan.id === "pro_monthly" && plan.interval === "month");
  const annual = plans.find((plan) => plan.id === "pro_annual" && plan.interval === "year");
  if (!monthly || !annual || !Number.isFinite(monthly.amount_minor) ||
    !Number.isFinite(annual.amount_minor) || monthly.amount_minor <= 0 || annual.amount_minor <= 0) return null;
  const savings = Math.round((1 - annual.amount_minor / (monthly.amount_minor * 12)) * 100);
  return savings > 0 ? `Save about ${savings}% with annual billing.` : null;
}

export interface ProviderSubscription {
  provider: string;
  plan: string;
  status: string;
  current_period_end: string | null;
  trial_end: string | null;
  cancel_at_period_end: boolean;
}

export interface SubscriptionOverview {
  entitlement_key: string;
  plan: string;
  status: string;
  active: boolean;
  starts_at: string | null;
  ends_at: string | null;
  provider_subscriptions: ProviderSubscription[];
}

interface StripeSessionResponse {
  url: string;
}

export async function getSubscription(): Promise<SubscriptionOverview> {
  const { data } = await client.get<SubscriptionOverview>("/subscriptions/me");
  return data;
}

export async function createCheckoutSession(plan: SubscriptionPlan): Promise<StripeSessionResponse> {
  const { data } = await client.post<StripeSessionResponse>("/subscriptions/checkout-session", {
    plan,
  });
  return data;
}

export async function createBillingPortalSession(): Promise<StripeSessionResponse> {
  const { data } = await client.post<StripeSessionResponse>("/subscriptions/billing-portal");
  return data;
}

export function redirectToExternal(url: string): void {
  window.location.assign(url);
}