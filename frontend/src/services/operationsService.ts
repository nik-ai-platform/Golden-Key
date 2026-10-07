import { client } from "../api/client";
import type { WorkerStatusResponse } from "../types/operations";

export async function getWorkerStatus(signal?: AbortSignal): Promise<WorkerStatusResponse> {
  const { data } = await client.get<WorkerStatusResponse>("/operations/workers", { signal });
  return data;
}
