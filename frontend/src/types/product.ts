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
  sportsbook: string | null;
  odds_observed_at: string | null;
  model_version: string;
  npi_score: number | null;
  confidence_score: number | null;
  simulation_probability: number | null;
  projected_edge: number | null;
  selected_side_edge?: number | null;
  edge_unit?: "percentage_points" | "scoring_points" | "unavailable";
  edge_benchmark?: string;
  risk_level: string | null;
  reasoning: string | null;
  outcome?: string | null;
  result_status?: string | null;
  recommendation_eligible?: boolean;
  recommendation_tier?: "PREFERRED" | "LOWER_PRIORITY" | "LOW_VALUE_HEAVY_FAVORITE" | null;
  recommendation_designation?: string | null;
  signal_breakdown?: PredictionSignalBreakdown | null;
}

export interface PredictionSignalBreakdown {
  model_version: string;
  prediction_recorded_at: string | null;
  factors: PredictionFactorRecord[];
  frozen_odds: FrozenOddsRecord | null;
  recorded_explanation?: string | null;
}

export interface PredictionFactorRecord {
  factor_name: string;
  weight: number | null;
  factor_score: number | null;
  predicted_side: string | null;
  recorded_at: string | null;
}

export interface FrozenOddsRecord {
  snapshot_id: number;
  sportsbook: string | null;
  spread_home: number | null;
  spread_away: number | null;
  spread_home_price: number | null;
  spread_away_price: number | null;
  moneyline_home: number | null;
  moneyline_away: number | null;
  total: number | null;
  total_over_price: number | null;
  total_under_price: number | null;
  recorded_at: string | null;
}

export interface TodayPredictionsResponse {
  sport: string | null;
  slate_date: string;
  count: number;
  predictions: Prediction[];
}

export interface UpcomingPredictionsResponse {
  sport: string | null;
  start_date: string;
  end_date: string;
  count: number;
  predictions: Prediction[];
}

export type DailyCardRole =
  "BEST_BET" | "TOP_SPREAD" | "TOP_MONEYLINE" | "TOP_TOTAL" | "VALUE_PLAY" | "NEXT_BEST";

export interface DailyCardPick {
  role: DailyCardRole;
  label: string;
  /** Older cached responses may contain this internal score; new responses omit it. */
  ranking_score?: number;
  ranking_reasons: string[];
  prediction: Prediction;
}

export interface DailyCardResponse {
  sport: string | null;
  generated_at: string;
  slate_date: string;
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
  npi_score: number | null;
  confidence_score: number | null;
  risk_level: string | null;
  outcome: string | null;
  result_status: string | null;
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
  npi_score: number | null;
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

export interface PerformanceIntelligenceSummary {
  total_bets: number;
  wins: number;
  losses: number;
  pushes: number;
  no_bets: number;
  win_rate: number;
  units_won: number;
  roi: number;
}

export interface PerformanceIntelligenceBreakdown
  extends PerformanceIntelligenceSummary {
  key: string;
}

export interface SpreadPerformanceSummary {
  sample_size: number;
  wins: number;
  losses: number;
  pushes: number;
  win_rate: number;
  units: number;
  roi: number;
}

export interface SpreadPerformanceBreakdown extends SpreadPerformanceSummary {
  key: string;
}

export interface SpreadProbabilityCalibration {
  key: string;
  sample_size: number;
  wins: number;
  losses: number;
  pushes: number;
  predicted_probability_average: number;
  actual_win_rate: number;
}

export interface Npi4SpreadPerformance {
  summary: SpreadPerformanceSummary;
  npi_bands: SpreadPerformanceBreakdown[];
  confidence_bands: SpreadPerformanceBreakdown[];
  projected_edge_bands: SpreadPerformanceBreakdown[];
  probability_calibration: SpreadProbabilityCalibration[];
  brier_score: number | null;
  brier_sample_size: number;
}

export interface PerformanceIntelligenceResponse {
  period_days: 7 | 30 | 90;
  generated_at: string;
  overall: PerformanceIntelligenceSummary;
  by_market: PerformanceIntelligenceBreakdown[];
  by_sport: PerformanceIntelligenceBreakdown[];
  by_npi_band: PerformanceIntelligenceBreakdown[];
  by_confidence_band: PerformanceIntelligenceBreakdown[];
  by_odds_band: PerformanceIntelligenceBreakdown[];
  by_side_type: PerformanceIntelligenceBreakdown[];
  by_model_version: PerformanceIntelligenceBreakdown[];
  npi_4_spread: Npi4SpreadPerformance;
  npi_5_spread?: Npi4SpreadPerformance;
}

export interface UserProfile {
  id: number;
  email: string;
  username: string;
  premium: boolean;
  recovery_email_masked?: string | null;
  recovery_email_verified?: boolean;
}
