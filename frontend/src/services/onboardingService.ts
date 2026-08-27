import { client } from "../api/client";

export type RegisterPayload = {
  username: string;
  email: string;
  password: string;
  accept_terms: boolean;
};

export type OnboardingStatus = {
  user_id: number;
  steps: {
    register: boolean;
    verify_email: boolean;
    favorite_sports: boolean;
    risk_profile: boolean;
    bankroll_settings: boolean;
  };
  progress_percent: number;
  next_route: string;
};

export async function registerUser(payload: RegisterPayload): Promise<{ user_id: number; message: string }> {
  const { data } = await client.post<{ user_id: number; message: string }>("/onboarding/register", payload);
  return data;
}

export async function getOnboardingStatus(userId: number): Promise<OnboardingStatus> {
  const { data } = await client.get<OnboardingStatus>(`/onboarding/status?user_id=${userId}`);
  return data;
}

export async function setFavoriteSports(userId: number, preferredSports: string[]): Promise<void> {
  await client.put("/onboarding/favorite-sports", {
    user_id: userId,
    preferred_sports: preferredSports,
  });
}

export async function setRiskProfile(userId: number, riskLevel: string): Promise<void> {
  await client.put("/onboarding/risk-profile", {
    user_id: userId,
    risk_level: riskLevel,
  });
}

export async function setBankrollSettings(userId: number, totalAmount: number, unitPercentage: number, maxDailyRisk: number): Promise<void> {
  await client.put("/onboarding/bankroll", {
    user_id: userId,
    total_amount: totalAmount,
    unit_percentage: unitPercentage,
    max_daily_risk: maxDailyRisk,
  });
}

export async function completeOnboarding(userId: number): Promise<void> {
  await client.post("/onboarding/complete", {
    user_id: userId,
  });
}
