import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Paper,
  Stack,
  Typography,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import { useQuery } from "@tanstack/react-query";

import { getWorkerStatus } from "../services/operationsService";
import type { WorkerCycle, WorkerHealth, WorkerStatus } from "../types/operations";

function timestamp(value: string | null) {
  return value === null ? "Unknown" : new Date(value).toLocaleString();
}

const healthColor: Record<WorkerHealth, "default" | "success" | "warning" | "error" | "info"> = {
  disabled: "default",
  unknown: "default",
  starting: "info",
  healthy: "success",
  warning: "warning",
  critical: "error",
  stopped: "warning",
};

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <Box sx={{ minWidth: 0, overflowWrap: "anywhere" }}>
      <Typography component="dt" variant="caption" color="text.secondary">
        {label}
      </Typography>
      <Typography component="dd" variant="body2" sx={{ m: 0 }}>
        {value}
      </Typography>
    </Box>
  );
}

function Cycle({ cycle, worker }: { cycle: WorkerCycle; worker: string }) {
  const label = `${worker} cycle ${cycle.sequence}: ${cycle.state}`;
  return (
    <Accordion disableGutters elevation={0} sx={{ border: "1px solid", borderColor: "divider" }}>
      <AccordionSummary
        expandIcon={<ExpandMoreIcon />}
        aria-controls={`${cycle.id}-sources`}
        id={`${cycle.id}-summary`}
      >
        <Stack spacing={0.25}>
          <Typography variant="body2" fontWeight={700}>
            {label}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {timestamp(cycle.started_at)} · {cycle.completed_sources}/{cycle.expected_sources}{" "}
            sources · {cycle.duration_ms === null ? "Duration unknown" : `${cycle.duration_ms} ms`}
          </Typography>
          <Typography variant="caption">
            Evidence: {cycle.telemetry_complete ? "complete" : "incomplete"} · Auxiliary errors:{" "}
            {cycle.auxiliary_errors}
          </Typography>
        </Stack>
      </AccordionSummary>
      <AccordionDetails id={`${cycle.id}-sources`} sx={{ minWidth: 0 }}>
        {cycle.error_code && <Alert severity="error">{cycle.error_code}</Alert>}
        <Stack spacing={1.5}>
          {cycle.sources.length === 0 && <Typography>No source evidence recorded.</Typography>}
          {cycle.sources.map((source) => (
            <Box
              key={`${source.sport}-${source.league}-${source.provider}-${source.provider_source}`}
              sx={{ p: 1.5, border: "1px solid", borderColor: "divider", overflowWrap: "anywhere" }}
            >
              <Typography component="h4" variant="subtitle2">
                {source.sport} · {source.league}
              </Typography>
              <Typography variant="caption">
                {source.provider} / {source.provider_source} · {source.state}
              </Typography>
              {source.error_code && <Alert severity="error">{source.error_code}</Alert>}
              <Box
                component="dl"
                sx={{
                  display: "grid",
                  gridTemplateColumns: {
                    xs: "repeat(2, minmax(0, 1fr))",
                    md: "repeat(4, minmax(0, 1fr))",
                  },
                  gap: 1,
                  mb: 0,
                }}
              >
                <Metric label="Started" value={timestamp(source.started_at)} />
                <Metric label="Finished" value={timestamp(source.finished_at)} />
                <Metric
                  label="Duration"
                  value={source.duration_ms === null ? "Unknown" : `${source.duration_ms} ms`}
                />
                {Object.entries(source.counters).map(([name, value]) => (
                  <Metric key={name} label={name.replace(/_/g, " ")} value={value ?? "Unknown"} />
                ))}
              </Box>
            </Box>
          ))}
        </Stack>
      </AccordionDetails>
    </Accordion>
  );
}

function WorkerPanel({ worker }: { worker: WorkerStatus }) {
  const instance = worker.latest_instance;
  return (
    <Paper
      component="section"
      aria-labelledby={`${worker.worker_name}-heading`}
      variant="outlined"
      sx={{ p: { xs: 1.5, sm: 2.5 }, minWidth: 0 }}
    >
      <Stack
        direction="row"
        alignItems="center"
        justifyContent="space-between"
        gap={1}
        flexWrap="wrap"
      >
        <Typography
          id={`${worker.worker_name}-heading`}
          component="h2"
          variant="h6"
          sx={{ overflowWrap: "anywhere" }}
        >
          {worker.worker_name}
        </Typography>
        <Chip label={worker.health} color={healthColor[worker.health]} size="small" />
      </Stack>
      <Stack spacing={1} sx={{ mt: 1 }}>
        {worker.alerts.map((alert) => (
          <Alert
            key={alert.code}
            severity={alert.severity === "critical" ? "error" : alert.severity}
          >
            {alert.message}
          </Alert>
        ))}
      </Stack>
      {instance ? (
        <Box
          component="dl"
          sx={{
            display: "grid",
            gridTemplateColumns: {
              xs: "repeat(2, minmax(0, 1fr))",
              md: "repeat(3, minmax(0, 1fr))",
            },
            gap: 1.5,
          }}
        >
          <Metric label="Instance" value={instance.id} />
          <Metric label="Lifecycle" value={instance.state} />
          <Metric
            label="Ownership observed"
            value={
              instance.ownership_held === null
                ? "Unknown"
                : instance.ownership_held
                  ? "Held"
                  : "Not held"
            }
          />
          <Metric label="Heartbeat" value={timestamp(instance.heartbeat_at)} />
          <Metric label="Main-loop progress" value={timestamp(instance.progress_at)} />
          <Metric label="Last success" value={timestamp(instance.last_success_at)} />
          <Metric label="Polling interval" value={`${instance.poll_seconds} seconds`} />
          <Metric
            label="Stale after"
            value={
              worker.stale_after_seconds === null
                ? "Unknown"
                : `${worker.stale_after_seconds} seconds`
            }
          />
          <Metric label="Telemetry failures recorded" value={instance.telemetry_failures} />
        </Box>
      ) : (
        <Typography sx={{ my: 2 }}>No instance evidence available.</Typography>
      )}
      <Typography component="h3" variant="subtitle2" sx={{ mt: 2, mb: 1 }}>
        Recent cycles for latest instance
      </Typography>
      <Stack spacing={1}>
        {worker.recent_cycles.length === 0 && (
          <Typography variant="body2">No cycle evidence available.</Typography>
        )}
        {worker.recent_cycles.map((cycle) => (
          <Cycle key={cycle.id} cycle={cycle} worker={worker.worker_name} />
        ))}
      </Stack>
      {worker.cycle_history_truncated && (
        <Typography variant="caption">
          Showing the latest 10 cycles; older history is not included.
        </Typography>
      )}
      {worker.recent_instances.length > 1 && (
        <Box sx={{ mt: 2 }}>
          <Typography component="h3" variant="subtitle2">
            Other recent instances
          </Typography>
          {worker.recent_instances.slice(1).map((other) => (
            <Typography
              key={other.id}
              variant="caption"
              display="block"
              sx={{ overflowWrap: "anywhere" }}
            >
              {other.id} · {other.state} · Ownership:{" "}
              {other.ownership_held === null
                ? "unknown"
                : other.ownership_held
                  ? "held"
                  : "not held"}
            </Typography>
          ))}
        </Box>
      )}
    </Paper>
  );
}

export function WorkerHealthPage() {
  const query = useQuery({
    queryKey: ["operations", "workers"],
    queryFn: ({ signal }) => getWorkerStatus(signal),
    refetchInterval: 30000,
    retry: false,
  });
  return (
    <Stack spacing={2} sx={{ minWidth: 0 }}>
      <Stack
        direction="row"
        justifyContent="space-between"
        alignItems="center"
        gap={1}
        flexWrap="wrap"
      >
        <Typography component="h1" variant="h4" className="gk-editorial">
          Worker Health
        </Typography>
        <Button variant="outlined" onClick={() => void query.refetch()} disabled={query.isFetching}>
          Refresh worker status
        </Button>
      </Stack>
      <Typography variant="body2" color="text.secondary">
        Read-only operational evidence. Ownership proves a retained telemetry connection, not
        continuous OS-process liveness. Unknown counters are not zero. Alerts are classifications
        only; this page sends no notifications or worker commands.
      </Typography>
      {query.isPending && (
        <Stack role="status" direction="row" alignItems="center" spacing={1}>
          <CircularProgress size={20} />
          <Typography>Loading worker evidence...</Typography>
        </Stack>
      )}
      {query.isError && (
        <Alert severity="error" role="alert">
          Worker status unavailable: {query.error.message}. Previously loaded evidence, if shown, is
          stale.
        </Alert>
      )}
      {query.data && (
        <>
          <Typography variant="caption" role="status" aria-live="polite">
            Evidence observed: {timestamp(query.data.observed_at)}
          </Typography>
          {!query.data.telemetry_enabled && (
            <Alert severity="info">
              Telemetry is disabled. Worker health is unknown; no storage query was performed.
            </Alert>
          )}
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: { xs: "minmax(0, 1fr)", lg: "repeat(2, minmax(0, 1fr))" },
              gap: 2,
            }}
          >
            {query.data.workers.map((worker) => (
              <WorkerPanel key={worker.worker_name} worker={worker} />
            ))}
          </Box>
        </>
      )}
    </Stack>
  );
}
