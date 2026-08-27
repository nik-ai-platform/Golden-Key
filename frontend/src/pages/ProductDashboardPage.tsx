import { Box, Grid2 as Grid, Stack, Typography } from "@mui/material";
import { useQuery } from "@tanstack/react-query";

import { EmptyState } from "../components/EmptyState";
import { DashboardHero } from "../components/DashboardHero";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { PredictionMetric } from "../components/PredictionMetric";
import { ProductPredictionCard } from "../components/ProductPredictionCard";
import { getPerformance, getTodayPredictions } from "../services/productApi";
import { checkApiHealth } from "../services/healthService";

export function ProductDashboardPage() {
  const predictions = useQuery({ queryKey: ["product", "today"], queryFn: () => getTodayPredictions() });
  const performance = useQuery({ queryKey: ["product", "performance"], queryFn: getPerformance });
  const health = useQuery({ queryKey: ["api", "health"], queryFn: checkApiHealth, refetchInterval: 30000 });

  if (predictions.isLoading || performance.isLoading) return <LoadingState message="Loading today's intelligence..." />;
  if (predictions.isError || performance.isError) {
    return <ErrorState kind="network" detail="Golden Key could not load the product dashboard." onRetry={() => { void predictions.refetch(); void performance.refetch(); }} />;
  }

  const predictionData = predictions.data!;
  const metrics = performance.data!;

  return (
    <Stack spacing={4}>
      <DashboardHero predictionCount={predictionData.count} />
      <Stack direction="row" spacing={1} alignItems="center" sx={{ mt: -2 }}>
        <Box sx={{ width: 8, height: 8, borderRadius: "50%", backgroundColor: health.data?.online ? "success.main" : "error.main" }} />
        <Typography variant="caption" color="text.secondary">
          {health.data?.online ? `API online${health.data.apiVersion ? ` · ${health.data.apiVersion}` : ""}` : "API unavailable"}
        </Typography>
      </Stack>

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, sm: 6, lg: 3 }}><PredictionMetric label="Tracked results" value={String(metrics.total_predictions)} /></Grid>
        <Grid size={{ xs: 12, sm: 6, lg: 3 }}><PredictionMetric label="Wins" value={String(metrics.wins)} /></Grid>
        <Grid size={{ xs: 12, sm: 6, lg: 3 }}><PredictionMetric label="Accuracy" value={`${metrics.accuracy.toFixed(1)}%`} /></Grid>
        <Grid size={{ xs: 12, sm: 6, lg: 3 }}><PredictionMetric label="Profit / loss" value={`${metrics.profit_loss >= 0 ? "+" : ""}$${metrics.profit_loss.toFixed(2)}`} /></Grid>
      </Grid>

      <Box>
        <Typography variant="h5">Top opportunities</Typography>
        <Typography color="text.secondary" sx={{ mt: 0.5, mb: 2 }}>Highest-confidence outputs for today's slate.</Typography>
        {predictionData.predictions.length ? (
          <Grid container spacing={2.5}>
            {predictionData.predictions.map((prediction, index) => (
              <Grid key={prediction.prediction_id} size={{ xs: 12, xl: 6 }}>
                <ProductPredictionCard prediction={prediction} rank={index + 1} />
              </Grid>
            ))}
          </Grid>
        ) : (
          <EmptyState title="No predictions available" description="Today's opportunities will appear after the prediction pipeline runs." />
        )}
      </Box>
    </Stack>
  );
}
