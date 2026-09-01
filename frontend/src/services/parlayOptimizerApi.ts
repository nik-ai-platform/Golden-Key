import { client } from "../api/client";

export type ParlayLeg = {
  prediction_id: number;
  game_id: number;
  sport: string;
  game_date: string;
  home_team: string;
  away_team: string;
  market: "spread" | "moneyline" | "total";
  selection: "HOME" | "AWAY" | "OVER" | "UNDER";
  display_selection: string;
  line_value: number | null;
  american_odds: number;
  npi_score: number;
  confidence_score: number;
  simulation_probability: number;
  projected_edge: number;
  risk_level: string;
  parlay_score: number;
  reasoning: string | null;
  sportsbook: string;
  odds_observed_at: string;
};

export type OptimizedParlay = {
  leg_count: number;
  generated_at: string;
  horizon_days: number;
  sport: string | null;
  legs: ParlayLeg[];
  average_npi: number;
  average_confidence: number;
  average_projected_edge: number;
  combined_american_odds: number;
  risk_level: string;
  market_mix: {
    spread: number;
    total: number;
    moneyline: number;
  };
};

export async function optimizeParlay(
  legs: number,
  sport?: string,
): Promise<OptimizedParlay> {
  const { data } = await client.get<OptimizedParlay>("/parlays/optimize", {
    params: { legs, sport: sport || undefined },
  });
  return data;
}