import { client } from "../api/client";

export type ModelStatusResponse = {
  status?: string;
  model_version?: string;
  validation_score?: number;
  calibration?: number;
  prediction_agreement?: number;
  health?: string;
};

export type ModelPerformanceResponse = {
  accuracy?: number;
  roi?: number;
  ats_percentage?: number;
  calibration?: number;
  feature_drift?: number;
  inference_latency_ms?: number;
  prediction_count?: number;
  version?: string;
};

export async function getModelStatus(): Promise<ModelStatusResponse> {
  const { data } = await client.get<ModelStatusResponse>("/models/status");
  return data;
}

export async function getModelPerformance(): Promise<ModelPerformanceResponse> {
  const { data } = await client.get<ModelPerformanceResponse>("/models/performance");
  return data;
}

export async function predictModel(payload: { game?: Record<string, unknown>; npi_score?: number; ml_prediction?: number }): Promise<Record<string, unknown>> {
  const { data } = await client.post<Record<string, unknown>>("/models/predict", payload);
  return data;
}

export async function explainModel(gameId: number): Promise<Record<string, unknown>> {
  const { data } = await client.get<Record<string, unknown>>(`/models/explain/${gameId}`);
  return data;
}
