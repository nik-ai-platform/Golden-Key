import { Box, Button, Grid2 as Grid, Stack, Typography } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";

import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { ProductPredictionCard } from "../components/ProductPredictionCard";
import { getTodayPredictions } from "../services/productApi";

const sports = ["NFL", "NBA", "NCAAF", "NCAAB", "WNBA"];

export function ProductGamesPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const sport = searchParams.get("sport") || undefined;
  const query = useQuery({ queryKey: ["product", "today", sport], queryFn: () => getTodayPredictions(sport) });

  if (query.isLoading) return <LoadingState message="Loading today's games..." />;
  if (query.isError) return <ErrorState kind="network" detail="Games could not be loaded." onRetry={() => void query.refetch()} />;

  return (
    <Stack spacing={3}>
      <Box>
        <Typography variant="h4">Today's games</Typography>
        <Typography color="text.secondary" sx={{ mt: 1 }}>Browse current model opportunities by sport.</Typography>
      </Box>
      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
        <Button variant={!sport ? "contained" : "outlined"} onClick={() => setSearchParams({})}>All</Button>
        {sports.map((item) => (
          <Button key={item} variant={sport === item ? "contained" : "outlined"} onClick={() => setSearchParams({ sport: item })}>{item}</Button>
        ))}
      </Stack>
      {query.data!.predictions.length ? (
        <Grid container spacing={2.5}>
          {query.data!.predictions.map((prediction) => (
            <Grid key={prediction.prediction_id} size={{ xs: 12, xl: 6 }}>
              <ProductPredictionCard prediction={prediction} />
            </Grid>
          ))}
        </Grid>
      ) : (
        <EmptyState
          title="No active opportunities"
          description={sport ? `Golden Key currently has no qualified ${sport} predictions for today's slate.` : "Golden Key currently has no qualified predictions for today's slate."}
        />
      )}
    </Stack>
  );
}
