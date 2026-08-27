import { client } from "../api/client";

export type SportModelResponse = {
  sport?: string;
  model?: string;
  health?: string;
};

export async function getSports(): Promise<SportModelResponse[]> {
  const { data } = await client.get<SportModelResponse[]>("/sports");
  return data;
}

export async function getSportModel(sport: string): Promise<SportModelResponse> {
  const { data } = await client.get<SportModelResponse>(`/sports/${sport}/model`);
  return data;
}

export async function getSportFeatures(sport: string): Promise<{ sport?: string; features?: string[] }> {
  const { data } = await client.get<{ sport?: string; features?: string[] }>(`/sports/${sport}/features`);
  return data;
}

export async function getSportComparison(): Promise<Record<string, unknown>> {
  const { data } = await client.get<Record<string, unknown>>("/sports/comparison");
  return data;
}
