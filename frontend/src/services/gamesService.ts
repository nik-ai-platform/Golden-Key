import { client } from "../api/client";
import type { Game } from "../types/games";

export async function getGames(): Promise<Game[]> {
  const { data } = await client.get<Game[]>("/games/");
  return data;
}
