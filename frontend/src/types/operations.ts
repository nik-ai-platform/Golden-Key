export type WorkerHealth =
  "disabled" | "unknown" | "starting" | "healthy" | "warning" | "critical" | "stopped";

export type WorkerAlert = {
  code: string;
  severity: "info" | "warning" | "critical";
  message: string;
};

export type WorkerSource = {
  sport: string;
  league: string;
  provider: string;
  provider_source: string;
  state: "pending" | "running" | "succeeded" | "partial" | "failed" | "missing";
  started_at: string | null;
  finished_at: string | null;
  duration_ms: number | null;
  error_code: string | null;
  counters: Record<string, number | null>;
};

export type WorkerCycle = {
  id: string;
  sequence: number;
  state: "running" | "succeeded" | "partial" | "failed" | "abandoned";
  started_at: string;
  finished_at: string | null;
  duration_ms: number | null;
  expected_sources: number;
  completed_sources: number;
  failed_sources: number;
  telemetry_complete: boolean;
  error_code: string | null;
  auxiliary_errors: number;
  sources: WorkerSource[];
};

export type WorkerInstance = {
  id: string;
  state: "starting" | "idle" | "running" | "stopped";
  started_at: string;
  heartbeat_at: string;
  progress_at: string;
  stopped_at: string | null;
  poll_seconds: number;
  heartbeat_seconds: number;
  schedule_mode: "after_completion" | "start_to_start";
  last_success_at: string | null;
  last_success_duration_ms: number | null;
  telemetry_failures: number;
  ownership_held: boolean | null;
};

export type WorkerStatus = {
  worker_name: "final-score-worker" | "upcoming-game-worker";
  health: WorkerHealth;
  alerts: WorkerAlert[];
  stale_after_seconds: number | null;
  latest_instance: WorkerInstance | null;
  recent_instances: WorkerInstance[];
  instance_history_truncated: boolean;
  recent_cycles: WorkerCycle[];
  cycle_history_truncated: boolean;
};

export type WorkerStatusResponse = {
  observed_at: string;
  telemetry_enabled: boolean;
  workers: WorkerStatus[];
};
