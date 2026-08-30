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

export interface Performance {
  total_predictions: number;
  wins: number;
  losses: number;
  pushes: number;
  accuracy: number;
  profit_loss: number;
}

export interface UserProfile {
  id: number;
  email: string;
  username: string;
  premium: boolean;
}
