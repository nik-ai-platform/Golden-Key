import { client } from "../api/client";

export type PreferencesResponse = {
  minimum_confidence?: number;
  minimum_edge?: number;
  max_parlay_legs?: number;
  avoid_high_variance?: boolean;
  preferred_odds_range?: string;
};

export async function getUserPreferences(): Promise<PreferencesResponse> {
  const { data } = await client.get<PreferencesResponse>("/preferences");
  return data;
}

export async function updateUserPreferences(payload: PreferencesResponse): Promise<PreferencesResponse> {
  const { data } = await client.put<PreferencesResponse>("/preferences", payload);
  return data;
}
