import { Box, Card, CardContent, Grid2 as Grid, Stack, Typography } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { NPIScore } from "../components/NPIScore";
import { PredictionMetric } from "../components/PredictionMetric";
import { SavePickButton } from "../components/SavePickButton";
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
  const prediction = game.prediction;

  return (
    <Stack spacing={3}>
      <Box>
        <Typography variant="overline" color="text.secondary">{game.sport}</Typography>
        <Typography variant="h4" sx={{ mt: 0.5 }}>{game.away_team} <Typography component="span" variant="h5" color="text.secondary">at</Typography> {game.home_team}</Typography>
        <Typography color="text.secondary" sx={{ mt: 1 }}>{new Date(game.game_date).toLocaleString()}</Typography>
      </Box>
      {!prediction ? <EmptyState title="No active prediction" description="No production analysis is available for this game." /> : (
        <>
          <Grid container spacing={2.5}>
            <Grid size={{ xs: 12, lg: 7 }}>
              <Card variant="outlined" sx={{ borderRadius: 2, height: "100%" }}><CardContent sx={{ p: 3 }}>
                <Typography color="text.secondary">Golden Key pick</Typography>
                <Typography variant="h4" sx={{ mt: 1, mb: 4 }}>{prediction.selection}</Typography>
                <NPIScore score={prediction.npi_score} />
              </CardContent></Card>
            </Grid>
            <Grid size={{ xs: 12, lg: 5 }}>
              <Grid container spacing={1.5}>
                <Grid size={{ xs: 12, sm: 6 }}><PredictionMetric label="Confidence" value={prediction.confidence_score == null ? "Not rated" : `${prediction.confidence_score.toFixed(1)}%`} /></Grid>
                <Grid size={{ xs: 12, sm: 6 }}><PredictionMetric label="Simulation" value={prediction.simulation_probability == null ? "Not rated" : `${prediction.simulation_probability.toFixed(1)}%`} /></Grid>
                <Grid size={{ xs: 12, sm: 6 }}><PredictionMetric label="Projected edge" value={prediction.projected_edge == null ? "Not rated" : `${prediction.projected_edge >= 0 ? "+" : ""}${prediction.projected_edge.toFixed(1)}%`} /></Grid>
                <Grid size={{ xs: 12, sm: 6 }}><PredictionMetric label="Risk" value={prediction.risk_level ?? "Unrated"} /></Grid>
              </Grid>
            </Grid>
          </Grid>
          <Card variant="outlined" sx={{ borderRadius: 2 }}><CardContent sx={{ p: 3 }}>
            <Typography variant="overline" color="text.secondary">Golden Key analysis</Typography>
            <Typography sx={{ mt: 1.5, lineHeight: 1.8 }}>{prediction.reasoning ?? "No analysis available."}</Typography>
            <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 2 }}>Model: {prediction.model_version}</Typography>
            <Box sx={{ mt: 3 }}><SavePickButton predictionId={prediction.prediction_id} /></Box>
          </CardContent></Card>
        </>
      )}
    </Stack>
  );
}
