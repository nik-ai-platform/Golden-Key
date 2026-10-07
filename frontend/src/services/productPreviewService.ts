import { client } from "../api/client";

export interface PreviewSlate {
  sport: string | null;
  count: number;
  games: { game_id: number; sport: string; league: string; home_team: string; away_team: string; start_time: string | null; status: string }[];
}

export async function getPreview(): Promise<PreviewSlate> {
  const { data } = await client.get<PreviewSlate>("/product/preview");
  return data;
}
