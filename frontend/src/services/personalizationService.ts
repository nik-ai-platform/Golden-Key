import { client } from "../api/client";

export type ProfileResponse = {
  user_id: number;
  risk_level?: string;
  preferred_sports?: string[];
  preferred_markets?: string[];
  betting_style?: string;
};

export async function getUserProfile(): Promise<ProfileResponse> {
  const { data } = await client.get<ProfileResponse>("/profile");
  return data;
}

export async function updateUserProfile(payload: Partial<ProfileResponse>): Promise<ProfileResponse> {
  const { data } = await client.put<ProfileResponse>("/profile", payload);
  return data;
}

export async function getPersonalizedRecommendations(): Promise<unknown[]> {
  const { data } = await client.get<unknown[]>("/recommendations/personalized");
  return data;
}
