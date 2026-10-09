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
  model_version?: string;
  confidence_score: number;
  simulation_probability: number;
  projected_edge: number;
  selected_side_edge?: number | null;
  edge_unit?: string;
  risk_level: string;
  /** Older cached responses may contain this internal score; new responses omit it. */
  parlay_score?: number;
  selection_reason?: string;
  reasoning: string | null;
  sportsbook: string;
  odds_observed_at: string;
};

export type OptimizedParlay = {
  leg_count: number;
  requested_leg_count?: number;
  adjustment_reason?: string | null;
  generated_at: string;
  horizon_days: number;
  sport: string | null;
  legs: ParlayLeg[];
  average_npi: number;
  average_confidence: number;
  average_model_probability?: number;
  /** Deprecated: unlike edge units must not be averaged. */
  average_projected_edge: number | null;
  average_projected_edge_deprecated?: boolean;
  average_selected_side_edge_by_market?: Record<string, { value: number | null; unit: string }>;
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