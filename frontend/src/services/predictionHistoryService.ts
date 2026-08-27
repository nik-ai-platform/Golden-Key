import { client } from "../api/client";
import type { PredictionHistoryEntry } from "../types/predictionHistory";

export async function listPredictionHistory(): Promise<PredictionHistoryEntry[]> {
  const { data } = await client.get<PredictionHistoryEntry[]>("/prediction-history");
  return data;
}

export async function exportPredictionHistory(): Promise<PredictionHistoryEntry[]> {
  const { data } = await client.get<PredictionHistoryEntry[]>("/prediction-history/export");
  return data;
}

export async function clearPredictionHistory(): Promise<{ deleted_count: number }> {
  const { data } = await client.delete<{ deleted_count: number }>("/prediction-history");
  return data;
}
