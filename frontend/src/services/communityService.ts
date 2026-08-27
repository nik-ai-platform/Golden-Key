import { client } from "../api/client";

export type CommunityProfileResponse = {
  username?: string;
  bio?: string;
  verified?: boolean;
};

export async function getCommunityProfile(): Promise<CommunityProfileResponse> {
  const { data } = await client.get<CommunityProfileResponse>("/community/profile");
  return data;
}

export async function getCommunityFeed(): Promise<Record<string, unknown>> {
  const { data } = await client.get<Record<string, unknown>>("/community/feed");
  return data;
}

export async function getCommunityLeaderboard(): Promise<Record<string, unknown>> {
  const { data } = await client.get<Record<string, unknown>>("/community/leaderboard");
  return data;
}

export async function getCommunityStrategies(): Promise<Record<string, unknown>> {
  const { data } = await client.get<Record<string, unknown>>("/community/strategies");
  return data;
}

export async function getCommunityDiscussions(): Promise<Record<string, unknown>> {
  const { data } = await client.get<Record<string, unknown>>("/community/discussions");
  return data;
}

export async function getCommunityReputation(): Promise<Record<string, unknown>> {
  const { data } = await client.get<Record<string, unknown>>("/community/reputation");
  return data;
}
