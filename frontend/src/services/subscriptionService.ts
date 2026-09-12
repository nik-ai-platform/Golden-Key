import { client } from "../api/client";

export const SUBSCRIPTION_PLANS = {
  pro_monthly: {
    name: "Golden Key Pro Monthly",
    billingLabel: "Monthly",
  },
  pro_annual: {
    name: "Golden Key Pro Annual",
    billingLabel: "Annual",
  },
} as const;

export type SubscriptionPlan = keyof typeof SUBSCRIPTION_PLANS;

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