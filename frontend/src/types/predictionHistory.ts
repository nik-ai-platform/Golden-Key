export type PredictionHistoryEntry = {
  id: number;
  game_id: number | null;
  model_version: string | null;
  prediction: string | null;
  confidence: number | null;
  spread_prediction: string | null;
  market_line: string | null;
  recommended_bet: string | null;
  result_status: string | null;
};
