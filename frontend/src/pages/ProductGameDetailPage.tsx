import { Box, Grid2 as Grid, Stack, Typography } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { ProductPredictionCard } from "../components/ProductPredictionCard";
import { NotFoundPage } from "./NotFoundPage";
import { getGameDetail } from "../services/productApi";

export function ProductGameDetailPage() {
  const { gameId } = useParams();
  const numericGameId = Number(gameId);
  const query = useQuery({
    queryKey: ["product", "game", numericGameId],
    queryFn: () => getGameDetail(numericGameId),
    enabled: Number.isInteger(numericGameId) && numericGameId > 0,
  });

  if (!Number.isInteger(numericGameId) || numericGameId <= 0) return <ErrorState kind="generic" detail="Invalid game identifier." />;
  if (query.isLoading) return <LoadingState message="Loading game analysis..." />;
  if (query.isError && "status" in query.error && query.error.status === 404) return <NotFoundPage />;
  if (query.isError) return <ErrorState kind="generic" detail="This game could not be loaded." onRetry={() => void query.refetch()} />;

  const game = query.data!;
  const predictions = game.predictions;

  return (
    <Stack spacing={3}>
      <Box>
        <Typography variant="overline" color="text.secondary">{game.sport}</Typography>
        <Typography variant="h4" sx={{ mt: 0.5 }}>{game.away_team} <Typography component="span" variant="h5" color="text.secondary">at</Typography> {game.home_team}</Typography>
        <Typography color="text.secondary" sx={{ mt: 1 }}>{new Date(game.game_date).toLocaleString()}</Typography>
      </Box>
      {!predictions.length ? <EmptyState title="No active prediction" description="No production analysis is available for this game." /> : (
        <Grid container spacing={2.5}>
          {predictions.map((prediction) => (
            <Grid key={prediction.prediction_id} size={{ xs: 12, xl: 4 }}>
              <ProductPredictionCard prediction={prediction} />
            </Grid>
          ))}
        </Grid>
      )}
    </Stack>
  );
}
