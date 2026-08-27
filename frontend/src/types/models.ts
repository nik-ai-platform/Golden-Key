export type ModelMetric = {
  accuracy: number;
  calibration: number;
  average_confidence: number;
  predictions: number;
};

export type ModelComparison = {
  current_model: ModelMetric;
  candidate_model: ModelMetric;
  winner: string;
};

export type ModelRegistryEntry = {
  model_version: string;
  release_date: string | null;
  feature_set: string[];
  evaluation_metrics: ModelMetric;
  deployment_status: string;
  evaluated_at: string;
};

export type CompareModelsRequest = {
  current_version: string;
  candidate_version: string;
  games?: Array<Record<string, unknown>>;
};