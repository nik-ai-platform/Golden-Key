export interface Prediction {
  prediction_id: number;
  game_id: number;
  sport: string;
  home_team: string;
  away_team: string;
  game_date: string;
  market: string;
  selection: string;
  display_selection: string;
  line_value: number | null;
  american_odds: number | null;
  model_version: string;
  npi_score: number;
  confidence_score: number | null;
  simulation_probability: number | null;
  projected_edge: number | null;
  risk_level: string | null;
  reasoning: string | null;
  outcome?: string | null;
}

export interface TodayPredictionsResponse {
  sport: string | null;
  count: number;
  predictions: Prediction[];
}

export type DailyCardRole =
  "BEST_BET" | "TOP_SPREAD" | "TOP_MONEYLINE" | "TOP_TOTAL" | "VALUE_PLAY" | "NEXT_BEST";

export interface DailyCardPick {
  role: DailyCardRole;
  label: string;
  ranking_score: number;
  ranking_reasons: string[];
  prediction: Prediction;
}

export interface DailyCardResponse {
  sport: string | null;
  generated_at: string;
  count: number;
  best_bet: DailyCardPick | null;
  featured_picks: DailyCardPick[];
  next_best: DailyCardPick[];
}

export interface GameDetail {
  game_id: number;
  sport: string;
  home_team: string;
  away_team: string;
  game_date: string;
  home_score: number | null;
  away_score: number | null;
  predictions: Prediction[];
}

export interface SavedPick {
  saved_pick_id: number;
  prediction_id: number;
  game_id: number;
  sport: string;
  game_date: string;
  home_team: string;
  away_team: string;
  matchup: string;
  market: string;
  selection: string;
  display_selection: string;
  line_value: number | null;
  american_odds: number | null;
  npi_score: number;
  confidence_score: number | null;
  risk_level: string | null;
  outcome: string | null;
  home_score: number | null;
  away_score: number | null;
}

export interface SavedPicksResponse {
  count: number;
  picks: SavedPick[];
}

export interface RemoveSavedPredictionResponse {
  removed: boolean;
  prediction_id: number;
}

export interface PerformanceBreakdown {
  name: string;
  settled: number;
  wins: number;
  losses: number;
  pushes: number;
  win_rate: number | null;
}

export interface RecentPerformanceResult {
  prediction_id: number;
  game_id: number;
  sport: string;
  game_date: string;
  home_team: string;
  away_team: string;
  market: string;
  display_selection: string;
  npi_score: number;
  outcome: "WIN" | "LOSS" | "PUSH";
  home_score: number | null;
  away_score: number | null;
}

export interface Performance {
  total_predictions: number;
  wins: number;
  losses: number;
  pushes: number;
  accuracy: number;
  profit_loss: number;
  market_performance: PerformanceBreakdown[];
  sport_performance: PerformanceBreakdown[];
  recent_results: RecentPerformanceResult[];
}

export interface UserProfile {
  id: number;
  email: string;
  username: string;
  premium: boolean;
  recovery_email_masked?: string | null;
  recovery_email_verified?: boolean;
}
