import { client } from "../api/client";
import type { Team, TeamIntelligence, TeamIntelligenceDetail } from "../types/teams";

export async function getTeams(): Promise<Team[]> {
  const { data } = await client.get<Team[]>("/teams/");
  return data;
}

export async function getTeamIntelligence(teamId: number): Promise<TeamIntelligence> {
  const { data } = await client.get<TeamIntelligence>(`/teams/${teamId}/intelligence`);
  return data;
}

export async function getTeamIntelligenceDetail(teamId: number): Promise<TeamIntelligenceDetail> {
  const { data } = await client.get<TeamIntelligenceDetail>(`/teams/${teamId}/intelligence/detail`);
  return data;
}
