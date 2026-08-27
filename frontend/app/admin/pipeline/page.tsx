import { useEffect, useState } from "react";
import {
  Alert,
  Button,
  Card,
  CardContent,
  Chip,
  Grid2 as Grid,
  LinearProgress,
  Stack,
  Typography,
} from "@mui/material";

import { getPipelineHealth, getPipelineStatus, runPipeline } from "../../../services/api";

type StatusPayload = {
  monitor?: {
    pipeline_status?: string;
    last_run?: string | null;
    duration?: number | null;
    success_rate?: number;
    failures?: number;
  };
  stages?: string[];
};

export default function PipelineAdminPage() {
  const [status, setStatus] = useState<StatusPayload>({});
  const [health, setHealth] = useState<Array<{ stage: string; healthy: boolean; message: string }>>([]);
  const [running, setRunning] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function refresh() {
    const [statusResponse, healthResponse] = await Promise.all([getPipelineStatus(), getPipelineHealth()]);
    setStatus(statusResponse);
    setHealth(healthResponse.pipeline_health || []);
  }

  async function executePipeline() {
    setRunning(true);
    setMessage(null);
    try {
      const result = await runPipeline();
      setMessage(`Pipeline ${result.status}`);
      await refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Pipeline execution failed");
    } finally {
      setRunning(false);
    }
  }

  useEffect(() => {
    refresh().catch(() => setMessage("Unable to load pipeline status"));
  }, []);

  const monitor = status.monitor || {};

  return (
    <Stack spacing={2.5}>
      <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" spacing={1.5} alignItems={{ xs: "flex-start", sm: "center" }}>
        <Stack spacing={0.5}>
          <Typography variant="h4">Pipeline Administration</Typography>
          <Typography color="text.secondary">Monitor stage health, trigger runs, and validate production data flow.</Typography>
        </Stack>
        <Button variant="contained" onClick={executePipeline} disabled={running}>
          {running ? "Running..." : "Run Pipeline"}
        </Button>
      </Stack>

      {running ? <LinearProgress /> : null}
      {message ? <Alert severity={message.includes("failed") || message.includes("Unable") ? "error" : "success"}>{message}</Alert> : null}

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 3 }}>
          <Card><CardContent><Typography variant="overline">Status</Typography><Typography variant="h5">{monitor.pipeline_status || "idle"}</Typography></CardContent></Card>
        </Grid>
        <Grid size={{ xs: 12, md: 3 }}>
          <Card><CardContent><Typography variant="overline">Success Rate</Typography><Typography variant="h5">{monitor.success_rate ?? 0}%</Typography></CardContent></Card>
        </Grid>
        <Grid size={{ xs: 12, md: 3 }}>
          <Card><CardContent><Typography variant="overline">Failures</Typography><Typography variant="h5">{monitor.failures ?? 0}</Typography></CardContent></Card>
        </Grid>
        <Grid size={{ xs: 12, md: 3 }}>
          <Card><CardContent><Typography variant="overline">Duration</Typography><Typography variant="h5">{monitor.duration ?? "-"}</Typography></CardContent></Card>
        </Grid>
      </Grid>

      <Card>
        <CardContent>
          <Typography variant="h6" sx={{ mb: 1.5 }}>Pipeline Stages</Typography>
          <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" sx={{ mb: 2 }}>
            {(status.stages || []).map((stage) => <Chip key={stage} label={stage} color="primary" variant="outlined" />)}
          </Stack>
          <Stack spacing={1}>
            {health.map((item) => (
              <Alert key={item.stage} severity={item.healthy ? "success" : "error"}>
                {item.stage}: {item.message}
              </Alert>
            ))}
          </Stack>
        </CardContent>
      </Card>
    </Stack>
  );
}
