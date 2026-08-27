import { Box, Grid2 as Grid, Stack, Typography } from "@mui/material";
import { useQuery } from "@tanstack/react-query";

import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { PredictionMetric } from "../components/PredictionMetric";
import { getPerformance } from "../services/productApi";

export function ProductPerformancePage() {
  const query = useQuery({ queryKey: ["product", "performance"], queryFn: getPerformance });

  if (query.isLoading) return <LoadingState message="Loading settled performance..." />;
  if (query.isError) return <ErrorState kind="network" detail="Performance could not be loaded." onRetry={() => void query.refetch()} />;

  const performance = query.data!;
  const metrics = [
    ["Predictions", String(performance.total_predictions)],
    ["Wins", String(performance.wins)],
    ["Losses", String(performance.losses)],
    ["Pushes", String(performance.pushes)],
    ["Accuracy", `${performance.accuracy.toFixed(2)}%`],
    ["Profit / loss", `${performance.profit_loss >= 0 ? "+" : ""}$${performance.profit_loss.toFixed(2)}`],
  ];

  return (
    <Stack spacing={3}>
      <Box>
        <Typography variant="h4">Performance</Typography>
        <Typography color="text.secondary" sx={{ mt: 1 }}>Settled Golden Key prediction results.</Typography>
      </Box>
      <Grid container spacing={2}>
        {metrics.map(([label, value]) => (
          <Grid key={label} size={{ xs: 12, sm: 6, lg: 4 }}><PredictionMetric label={label} value={value} /></Grid>
        ))}
      </Grid>
    </Stack>
  );
}
