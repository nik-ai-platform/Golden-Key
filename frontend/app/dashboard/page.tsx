import { useEffect, useState } from "react";
import { Alert, Box, Button, Card, CardContent, Grid2 as Grid, Skeleton, Stack, Typography } from "@mui/material";

import AIAnalysisPanel from "../../components/AIAnalysisPanel";
import NPIIndicator from "../../components/NPIIndicator";
import PredictionCard from "../../components/PredictionCard";
import UserProfile from "../../components/UserProfile";
import { getBacktests, getModelFactors, getPredictions, runPipeline } from "../../services/api";
import type { Prediction } from "../../types/prediction";

type ModelPerformanceSummary = {
  currentVersion: string;
  ats: number;
  roi: number;
  games: number;
  bestFactor: string;
};

export default function DashboardPage() {
  const [predictions, setPredictions] = useState<Prediction[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [modelPerformance, setModelPerformance] = useState<ModelPerformanceSummary>({
    currentVersion: "N/A",
    ats: 0,
    roi: 0,
    games: 0,
    bestFactor: "N/A",
  });

  async function loadPredictions() {
    try {
      setError(null);
      const response = await getPredictions();
      const items = Array.isArray(response) ? response : response?.predictions ?? response?.data ?? [];
      setPredictions(items);
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : "Failed to load predictions");
    }
  }

  useEffect(() => {
    let mounted = true;

    (async () => {
      try {
        const response = await getPredictions();
        if (!mounted) {
          return;
        }

        const items = Array.isArray(response) ? response : response?.predictions ?? response?.data ?? [];
        setPredictions(items);
      } catch (loadError) {
        if (mounted) {
          setError(loadError instanceof Error ? loadError.message : "Failed to load predictions");
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    })();

    (async () => {
      try {
        const [backtests, modelFactors] = await Promise.all([getBacktests(), getModelFactors()]);
        if (!mounted) {
          return;
        }

        const latestRun = Array.isArray(backtests?.runs) ? backtests.runs[0] : null;
        const bestFactorName = Array.isArray(modelFactors?.top_factors) && modelFactors.top_factors.length > 0
          ? String(modelFactors.top_factors[0]?.factor ?? "N/A")
          : "N/A";

        setModelPerformance({
          currentVersion: String(latestRun?.model ?? modelFactors?.version ?? "N/A"),
          ats: Number(latestRun?.accuracy ?? modelFactors?.ats_accuracy ?? 0),
          roi: Number(latestRun?.roi ?? 0),
          games: Number(latestRun?.games ?? 0),
          bestFactor: bestFactorName,
        });
      } catch {
        if (mounted) {
          setModelPerformance((previous) => ({
            ...previous,
            bestFactor: "Unavailable",
          }));
        }
      }
    })();

    return () => {
      mounted = false;
    };
  }, []);

  async function handleRunPipeline() {
    setRefreshing(true);
    setError(null);

    try {
      await runPipeline();
      await loadPredictions();
    } catch (runError) {
      setError(runError instanceof Error ? runError.message : "Pipeline refresh failed");
    } finally {
      setRefreshing(false);
    }
  }

  const topPrediction = predictions[0];

  return (
    <Stack spacing={2.5}>
      <Stack spacing={0.5}>
        <Typography variant="h4">Golden Key Dashboard</Typography>
        <Typography color="text.secondary">Main command center for opportunities, intelligence, and performance.</Typography>
      </Stack>

      <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
        <Button variant="contained" onClick={handleRunPipeline} disabled={refreshing}>
          {refreshing ? "Refreshing..." : "Run pipeline"}
        </Button>
        <Button variant="outlined" onClick={loadPredictions} disabled={loading}>
          Refresh predictions
        </Button>
      </Stack>

      {error ? <Alert severity="error">{error}</Alert> : null}

  <UserProfile />

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 7 }}>
          {loading ? (
            <Card>
              <CardContent>
                <Skeleton variant="text" width="35%" height={40} />
                <Skeleton variant="rounded" height={280} />
              </CardContent>
            </Card>
          ) : topPrediction ? (
            <PredictionCard prediction={topPrediction} matchup={`Game ${topPrediction.game_id}`} />
          ) : (
            <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  No predictions yet
                </Typography>
                <Typography color="text.secondary">
                  Run the pipeline to generate fresh predictions from the backend.
                </Typography>
              </CardContent>
            </Card>
          )}
        </Grid>
        <Grid size={{ xs: 12, md: 5 }}>
          <Card sx={{ height: "100%" }}>
            <CardContent>
              <Typography variant="h6" sx={{ mb: 1.5 }}>
                Top NPI Scores
              </Typography>
              <Stack spacing={1.5}>
                {(predictions.slice(0, 3).length > 0 ? predictions.slice(0, 3) : [
                  { id: 1, game_id: 1, market: "Spread", selection: "Sample", npi_score: 87, win_probability: 0, confidence_score: 0, projected_edge: 0, risk_level: "Medium", reasoning: "Loading sample", simulation_probability: 0, simulation_runs: 0, simulation_margin: 0 },
                ]).map((prediction) => (
                  <NPIIndicator key={prediction.id} score={prediction.npi_score} label={`Game ${prediction.game_id}`} />
                ))}
              </Stack>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 4 }}>
          <Card>
            <CardContent>
              <Typography variant="overline">AI Alerts</Typography>
              <Typography variant="h4">{predictions.length}</Typography>
              <Typography color="text.secondary">Generated predictions available now</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <Card>
            <CardContent>
              <Typography variant="overline">Portfolio Status</Typography>
              <Typography variant="h4">Active</Typography>
              <Typography color="text.secondary">Live backend API and pipeline enabled</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <Card>
            <CardContent>
              <Typography variant="overline">Recent Performance</Typography>
              <Typography variant="h4">Ready</Typography>
              <Typography color="text.secondary">Dashboard now reflects API output</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Model Performance
          </Typography>
          <Grid container spacing={2}>
            <Grid size={{ xs: 12, sm: 6, md: 2.4 }}>
              <Typography variant="overline">Current Version</Typography>
              <Typography variant="h6">{modelPerformance.currentVersion}</Typography>
            </Grid>
            <Grid size={{ xs: 12, sm: 6, md: 2.4 }}>
              <Typography variant="overline">ATS</Typography>
              <Typography variant="h6">{modelPerformance.ats.toFixed(1)}%</Typography>
            </Grid>
            <Grid size={{ xs: 12, sm: 6, md: 2.4 }}>
              <Typography variant="overline">ROI</Typography>
              <Typography variant="h6">{modelPerformance.roi.toFixed(2)}%</Typography>
            </Grid>
            <Grid size={{ xs: 12, sm: 6, md: 2.4 }}>
              <Typography variant="overline">Games</Typography>
              <Typography variant="h6">{modelPerformance.games}</Typography>
            </Grid>
            <Grid size={{ xs: 12, sm: 6, md: 2.4 }}>
              <Typography variant="overline">Best Factor</Typography>
              <Typography variant="h6">{modelPerformance.bestFactor}</Typography>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      <Box>
        <AIAnalysisPanel
          title="Why this opportunity ranks first"
          reasons={[
            "Defensive efficiency projects above market assumptions.",
            "Model sees undervalued line movement.",
            "Simulation probability exceeds implied odds.",
          ]}
          mainRisk="Injury uncertainty on the away rotation"
        />
      </Box>
    </Stack>
  );
}
