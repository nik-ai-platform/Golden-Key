import { client } from "../api/client";

export type ModelOperationsResponse = {
  champion?: string;
  status?: string;
  health?: string;
  roi?: number;
  drift?: string;
  calibration?: number;
  training_queue?: number;
};

export async function getChampionModel(): Promise<ModelOperationsResponse> {
  const { data } = await client.get<ModelOperationsResponse>("/models/champion");
  return data;
}

export async function getModelDrift(): Promise<Record<string, unknown>> {
  const { data } = await client.get<Record<string, unknown>>("/models/drift");
  return data;
}

export async function getTrainingJobs(): Promise<Record<string, unknown>[]> {
  const { data } = await client.get<Record<string, unknown>[]>("/models/jobs");
  return data;
}

export async function promoteModel(): Promise<Record<string, unknown>> {
  const { data } = await client.post<Record<string, unknown>>("/models/promote", {});
  return data;
}

export async function rollbackModel(): Promise<Record<string, unknown>> {
  const { data } = await client.post<Record<string, unknown>>("/models/rollback", {});
  return data;
}
