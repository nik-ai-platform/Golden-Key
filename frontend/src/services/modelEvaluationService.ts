import { client } from "../api/client";
import type { CompareModelsRequest, ModelComparison, ModelRegistryEntry } from "../types/models";

export async function getModels(): Promise<ModelRegistryEntry[]> {
  const { data } = await client.get<ModelRegistryEntry[]>("/models");
  return data;
}

export async function getModel(version: string): Promise<ModelRegistryEntry> {
  const { data } = await client.get<ModelRegistryEntry>(`/models/${version}`);
  return data;
}

export async function compareModels(payload: CompareModelsRequest): Promise<ModelComparison> {
  const { data } = await client.post<ModelComparison>("/models/compare", payload);
  return data;
}