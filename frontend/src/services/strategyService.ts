import { client } from "../api/client";

export type StrategyResponse = {
  id?: number;
  strategy_name?: string;
  sport?: string;
  market_type?: string;
  rules?: Record<string, unknown>;
  starting_bankroll?: number;
};

export async function createStrategy(payload: Record<string, unknown>): Promise<StrategyResponse> {
  const { data } = await client.post<StrategyResponse>("/strategies", payload);
  return data;
}

export async function listStrategies(): Promise<StrategyResponse[]> {
  const { data } = await client.get<StrategyResponse[]>("/strategies");
  return data;
}

export async function simulateStrategy(payload: Record<string, unknown>): Promise<unknown> {
  const { data } = await client.post("/strategies/simulate", payload);
  return data;
}
