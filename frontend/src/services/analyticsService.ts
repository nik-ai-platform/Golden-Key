import { client } from "../api/client";
import type {
  AccuracyResponse,
  BacktestingResponse,
  CalibrationAnalytics,
  ConfidenceAnalytics,
  ModelLearningSummary,
  TrendPoint,
} from "../types/analytics";

export async function getAccuracy(): Promise<AccuracyResponse> {
  const { data } = await client.get<AccuracyResponse>("/analytics/accuracy");
  return data;
}

export async function getConfidence(): Promise<ConfidenceAnalytics> {
  const { data } = await client.get<ConfidenceAnalytics>("/analytics/confidence");
  return data;
}

export async function getDailyTrends(): Promise<TrendPoint[]> {
  const { data } = await client.get<TrendPoint[]>("/analytics/trends/daily");
  return data;
}

export async function getBacktesting(): Promise<BacktestingResponse> {
  const { data } = await client.get<BacktestingResponse>("/analytics/backtesting");
  return data;
}

export async function getCalibration(): Promise<CalibrationAnalytics> {
  const { data } = await client.get<CalibrationAnalytics>("/analytics/calibration");
  return data;
}

export async function getModelLearning(): Promise<ModelLearningSummary> {
  const { data } = await client.get<ModelLearningSummary>("/analytics/model-learning");
  return data;
}
