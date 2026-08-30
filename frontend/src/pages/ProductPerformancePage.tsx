import {
  Box,
  Card,
  CardContent,
  Divider,
  Grid2 as Grid,
  Stack,
  Typography,
} from "@mui/material";
import { useQuery } from "@tanstack/react-query";

import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { PredictionMetric } from "../components/PredictionMetric";
import { getPerformance } from "../services/productApi";

export function ProductPerformancePage() {
  const query = useQuery({
    queryKey: ["product", "performance"],
    queryFn: getPerformance,
  });

  if (query.isLoading) {
    return <LoadingState message="Loading settled performance..." />;
  }

  if (query.isError) {
    return (
      <ErrorState
        kind="network"
        detail="Performance could not be loaded."
        onRetry={() => void query.refetch()}
      />
    );
  }

  const performance = query.data!;

  const record = `${performance.wins}-${performance.losses}${
    performance.pushes ? `-${performance.pushes}` : ""
  }`;

  const profitLoss = `${performance.profit_loss >= 0 ? "+" : ""}$${performance.profit_loss.toFixed(2)}`;

  return (
    <Stack spacing={4}>
      <Box>
        <Typography variant="h4" fontWeight={700}>
          Performance
        </Typography>

        <Typography color="text.secondary" sx={{ mt: 1 }}>
          Results from settled Golden Key predictions.
        </Typography>
      </Box>

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 4 }}>
          <PredictionMetric
            label="Record"
            value={record}
          />
        </Grid>

        <Grid size={{ xs: 12, md: 4 }}>
          <PredictionMetric
            label="Accuracy"
            value={`${performance.accuracy.toFixed(1)}%`}
          />
        </Grid>

        <Grid size={{ xs: 12, md: 4 }}>
          <PredictionMetric
            label="Profit / Loss"
            value={profitLoss}
          />
        </Grid>
      </Grid>

      <Card
        variant="outlined"
        sx={{
          borderRadius: 3,
        }}
      >
        <CardContent
          sx={{
            p: { xs: 2.5, md: 3 },
            "&:last-child": {
              pb: { xs: 2.5, md: 3 },
            },
          }}
        >
          <Stack spacing={3}>
            <Box>
              <Typography variant="h6" fontWeight={700}>
                Settled Results
              </Typography>

              <Typography
                variant="body2"
                color="text.secondary"
                sx={{ mt: 0.5 }}
              >
                Breakdown of all predictions with a final result.
              </Typography>
            </Box>

            <Divider />

            <Grid container spacing={3}>
              <Grid size={{ xs: 6, sm: 3 }}>
                <Stack spacing={0.5}>
                  <Typography variant="body2" color="text.secondary">
                    Total
                  </Typography>

                  <Typography variant="h5" fontWeight={700}>
                    {performance.total_predictions}
                  </Typography>
                </Stack>
              </Grid>

              <Grid size={{ xs: 6, sm: 3 }}>
                <Stack spacing={0.5}>
                  <Typography variant="body2" color="text.secondary">
                    Wins
                  </Typography>

                  <Typography variant="h5" fontWeight={700}>
                    {performance.wins}
                  </Typography>
                </Stack>
              </Grid>

              <Grid size={{ xs: 6, sm: 3 }}>
                <Stack spacing={0.5}>
                  <Typography variant="body2" color="text.secondary">
                    Losses
                  </Typography>

                  <Typography variant="h5" fontWeight={700}>
                    {performance.losses}
                  </Typography>
                </Stack>
              </Grid>

              <Grid size={{ xs: 6, sm: 3 }}>
                <Stack spacing={0.5}>
                  <Typography variant="body2" color="text.secondary">
                    Pushes
                  </Typography>

                  <Typography variant="h5" fontWeight={700}>
                    {performance.pushes}
                  </Typography>
                </Stack>
              </Grid>
            </Grid>
          </Stack>
        </CardContent>
      </Card>
    </Stack>
  );
}
