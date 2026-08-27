export type PredictionResponse = {
  game_id: number;
  game_date: string;
  home_team: string;
  away_team: string;
  winner: string;
  confidence: number;
  nik_power_index: number;
  home_npi: number;
  away_npi: number;
  model_version: string;
};
