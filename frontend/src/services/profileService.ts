import { client } from "../api/client";

export type ProfileIntelligenceResponse = {
  user_id?: number;
  risk_level?: string;
  preferred_sports?: string[];
  preferred_bet_types?: string[];
  average_stake?: number;
  favorite_markets?: string[];
  confidence_threshold?: number;
};

export async function getProfileIntelligence(userId = 1): Promise<ProfileIntelligenceResponse> {
  const { data } = await client.get<ProfileIntelligenceResponse>(`/profile/intelligence?user_id=${userId}`);
  return data;
}

export async function getProfilePerformance(userId = 1): Promise<Record<string, unknown>> {
  const { data } = await client.get<Record<string, unknown>>(`/profile/performance?user_id=${userId}`);
  return data;
}

export async function getProfileBriefing(userId = 1): Promise<Record<string, unknown>> {
  const { data } = await client.get<Record<string, unknown>>(`/profile/briefing?user_id=${userId}`);
  return data;
}

export async function getProfileRecommendations(userId = 1): Promise<Record<string, unknown>> {
  const { data } = await client.get<Record<string, unknown>>(`/profile/recommendations?user_id=${userId}`);
  return data;
}

export type ProfilePreferencesPayload = {
  user_id?: number;
  risk_level?: string;
  preferred_sports?: string[];
  preferred_bet_types?: string[];
  confidence_threshold?: number;
};

export async function updateProfilePreferences(payload: ProfilePreferencesPayload): Promise<Record<string, unknown>> {
  const { data } = await client.put<Record<string, unknown>>("/profile/preferences", payload);
  return data;
}
