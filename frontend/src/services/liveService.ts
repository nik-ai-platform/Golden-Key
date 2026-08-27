import { client } from "../api/client";

export type LiveGameResponse = {
  game_id?: number;
  home_score?: number;
  away_score?: number;
  quarter_period?: string;
  clock?: string;
  possession?: string;
  momentum_score?: number;
};

export type LiveProbabilityResponse = {
  game_id?: number;
  win_probability?: number;
  cover_probability?: number;
  total_probability?: number;
};

export type LiveSignalResponse = {
  signal?: string;
  message?: string;
  details?: Record<string, unknown>;
};

export type LiveAlertResponse = {
  alert?: string;
  details?: Record<string, unknown>;
};

export type LiveStreamResponse = {
  event?: string;
  status?: string;
};

export async function getLiveGames(): Promise<LiveGameResponse[]> {
  const { data } = await client.get<LiveGameResponse[]>("/live/games");
  return data;
}

export async function getLiveGame(gameId: number): Promise<LiveGameResponse> {
  const { data } = await client.get<LiveGameResponse>(`/live/${gameId}`);
  return data;
}

export async function getLiveProbability(gameId: number): Promise<LiveProbabilityResponse> {
  const { data } = await client.get<LiveProbabilityResponse>(`/live/probability/${gameId}`);
  return data;
}

export async function getLiveSignals(): Promise<LiveSignalResponse> {
  const { data } = await client.get<LiveSignalResponse>("/live/signals");
  return data;
}

export async function getLiveAlerts(): Promise<LiveAlertResponse> {
  const { data } = await client.get<LiveAlertResponse>("/live/alerts");
  return data;
}

export async function getLiveStream(): Promise<LiveStreamResponse> {
  const { data } = await client.get<LiveStreamResponse>("/live/stream");
  return data;
}
