export type DashboardModelVersion = {
  model: string;
  accuracy?: number;
};

export type DashboardResponse = {
  system_health: string;
  overall_accuracy: number;
  total_predictions: number;
  recent_predictions: unknown[];
  top_teams: unknown[];
  model_versions: DashboardModelVersion[];
};
