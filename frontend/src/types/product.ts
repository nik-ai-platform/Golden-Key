export interface Prediction {
  prediction_id: number;
  game_id: number;
  sport: string;
  home_team: string;
  away_team: string;
  game_date: string;
  market: string;
  selection: string;
  model_version: string;
  npi_score: number;
  confidence_score: number | null;
  simulation_probability: number | null;
  projected_edge: number | null;
  risk_level: string | null;
  reasoning: string | null;
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
  prediction: Prediction | null;
}

export interface SavedPick {
  saved_pick_id: number;
  prediction_id: number;
  game_id: number;
  market: string;
  selection: string;
  confidence_score: number | null;
  outcome: string | null;
}

export interface SavedPicksResponse {
  count: number;
  picks: SavedPick[];
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
