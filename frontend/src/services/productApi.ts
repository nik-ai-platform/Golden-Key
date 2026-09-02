import { client } from "../api/client";
import type {
  DailyCardResponse,
  GameDetail,
  Performance,
  PerformanceIntelligenceResponse,
  RemoveSavedPredictionResponse,
  SavedPicksResponse,
  TodayPredictionsResponse,
  UserProfile,
} from "../types/product";

export async function getDailyCard(sport?: string): Promise<DailyCardResponse> {
  const { data } = await client.get<DailyCardResponse>("/product/daily-card", {
    params: { sport: sport || undefined },
  });
  return data;
}

export async function getTodayPredictions(
  sport?: string,
  includePasses = false,
): Promise<TodayPredictionsResponse> {
  const { data } = await client.get<TodayPredictionsResponse>("/product/predictions/today", {
    params: {
      sport: sport || undefined,
      include_passes: includePasses || undefined,
    },
  });
  return data;
}

export async function getGameDetail(gameId: number): Promise<GameDetail> {
  const { data } = await client.get<GameDetail>(`/product/games/${gameId}`);
  return data;
}

export async function getPerformance(): Promise<Performance> {
  const { data } = await client.get<Performance>("/product/performance");
  return data;
}

export async function getPerformanceIntelligence(
  days: 7 | 30 | 90 = 30,
): Promise<PerformanceIntelligenceResponse> {
  const { data } = await client.get<PerformanceIntelligenceResponse>(
    "/product/performance-intelligence",
    { params: { days } },
  );
  return data;
}

export async function getProfile(): Promise<UserProfile> {
  const { data } = await client.get<UserProfile>("/users/me");
  return data;
}

export async function getSavedPicks(): Promise<SavedPicksResponse> {
  const { data } = await client.get<SavedPicksResponse>("/product/me/saved-picks");
  return data;
}

export async function savePrediction(predictionId: number): Promise<void> {
  await client.post("/users/save-prediction", {
    prediction_id: predictionId,
  });
}

export async function removeSavedPrediction(
  predictionId: number,
): Promise<RemoveSavedPredictionResponse> {
  const { data } = await client.delete<RemoveSavedPredictionResponse>(
    `/users/saved-predictions/${predictionId}`,
  );
  return data;
}
