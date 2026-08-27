export type ConfidenceBucket = {
  label: string;
  predictions: number;
  accuracy: number;
};

export type ConfidenceAnalytics = {
  average_confidence: number;
  highest_confidence: number;
  lowest_confidence: number;
  buckets: ConfidenceBucket[];
};

export type CalibrationBucket = {
  range: string;
  confidence: number;
  accuracy: number;
  error: number;
  predictions: number;
  wins: number;
  losses: number;
};

export type CalibrationAnalytics = {
  overall_error: number;
  mean_calibration_error: number;
  maximum_error: number;
  bucket_variance: number;
  overall_reliability: number;
  total_predictions: number;
  buckets: CalibrationBucket[];
};

export type TrendPoint = {
  period: string;
  accuracy: number;
  confidence: number;
  predictions: number;
  correct?: number | null;
};

export type AccuracyResponse = {
  overall_accuracy: number;
  sport_accuracy: Record<string, { total: number; correct: number; accuracy: number }>;
  model_accuracy: Record<string, { total: number; correct: number; accuracy: number }>;
  confidence_accuracy: Record<string, number>;
  dashboard_statistics: {
    overall_accuracy: number;
    recent_predictions: unknown[];
  };
};

export type BacktestingResponse = {
  snapshots_processed: number;
  evaluations_created: number;
  model_versions: string[];
};

export type ModelLearningSummary = {
  current_model: string;
  training_samples: number;
  candidate_models: number;
  best_candidate: string | null;
};
