import {
  NEUTRAL_TEAM_IDENTITY,
  TEAM_ALIASES,
  TEAM_IDENTITIES,
  type TeamIdentity,
} from "../data/teamIdentity";
import type { Prediction } from "../types/product";

function normalize(value: string): string {
  return value.trim().replace(/\s+/g, " ").toLocaleLowerCase("en-US");
}

const identityLookup = new Map(
  Object.entries(TEAM_IDENTITIES).map(([key, identity]) => [normalize(key), identity]),
);

const aliasLookup = new Map(
  Object.entries(TEAM_ALIASES).map(([key, team]) => [normalize(key), team]),
);

const teamNamesBySport = Object.keys(TEAM_IDENTITIES).reduce<Map<string, string[]>>(
  (teams, key) => {
    const separator = key.indexOf(":");
    const sport = key.slice(0, separator);
    const team = key.slice(separator + 1);
    teams.set(sport, [...(teams.get(sport) ?? []), team]);
    return teams;
  },
  new Map(),
);

export function getTeamIdentity(sport: string, team: string | null | undefined): TeamIdentity {
  if (!team) return NEUTRAL_TEAM_IDENTITY;

  const sportKey = sport.trim().toLocaleUpperCase("en-US");
  const teamKey = team.trim();
  const rawKey = `${sportKey}:${teamKey}`;
  const canonicalTeam = aliasLookup.get(normalize(rawKey)) ?? teamKey;
  return identityLookup.get(normalize(`${sportKey}:${canonicalTeam}`)) ?? NEUTRAL_TEAM_IDENTITY;
}

export function getPredictionTeam(prediction: Prediction): string | null {
  const selection = prediction.selection.trim().toLocaleUpperCase("en-US");
  if (selection === "HOME") return prediction.home_team;
  if (selection === "AWAY") return prediction.away_team;
  if (/^(OVER|UNDER)\b/.test(selection)) return null;

  const sport = prediction.sport.trim().toLocaleUpperCase("en-US");
  const normalizedSelection = normalize(prediction.selection);
  const directTeam = teamNamesBySport
    .get(sport)
    ?.sort((left, right) => right.length - left.length)
    .find((team) => normalizedSelection.startsWith(normalize(team)));
  if (directTeam) return directTeam;

  const alias = [...aliasLookup.entries()]
    .filter(([key]) => key.startsWith(`${normalize(sport)}:`))
    .sort(([left], [right]) => right.length - left.length)
    .find(([key]) => normalizedSelection.startsWith(key.slice(key.indexOf(":") + 1)));
  return alias?.[1] ?? null;
}

export function getPredictionTeamIdentity(prediction: Prediction): TeamIdentity {
  return getTeamIdentity(prediction.sport, getPredictionTeam(prediction));
}

export function hexToRgbChannels(hex: string): string {
  const normalized = hex.replace("#", "");
  const value = Number.parseInt(normalized, 16);
  return `${(value >> 16) & 255}, ${(value >> 8) & 255}, ${value & 255}`;
}