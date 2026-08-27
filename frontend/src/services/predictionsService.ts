import { client } from "../api/client";
import type { PredictionResponse } from "../types/predictions";

export async function getPrediction(gameId: number): Promise<PredictionResponse> {
  const { data } = await client.get<PredictionResponse>(`/predictions/${gameId}`);
  return data;
}

export async function listPredictions(params: {
  winner?: string;
  minConfidence?: number;
  sortBy?: "confidence" | "nik_power_index" | "game_date" | "model_version" | "winner";
  sortOrder?: "asc" | "desc";
  limit?: number;
}): Promise<PredictionResponse[]> {
  const { data } = await client.get<PredictionResponse[]>("/predictions", {
    params: {
      winner: params.winner || undefined,
      min_confidence: params.minConfidence,
      sort_by: params.sortBy,
      sort_order: params.sortOrder,
      limit: params.limit ?? 40,
    },
  });
  return data;
}
