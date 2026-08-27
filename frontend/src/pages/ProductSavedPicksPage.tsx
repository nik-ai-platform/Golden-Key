import { Card, CardActionArea, CardContent, Chip, Stack, Typography } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { getSavedPicks } from "../services/productApi";

export function ProductSavedPicksPage() {
  const navigate = useNavigate();
  const query = useQuery({ queryKey: ["product", "saved-picks"], queryFn: getSavedPicks });

  if (query.isLoading) return <LoadingState message="Loading saved picks..." />;
  if (query.isError) return <ErrorState kind="generic" detail="Unable to load saved picks." onRetry={() => void query.refetch()} />;
  if (!query.data?.picks.length) return <EmptyState title="No saved picks" description="Save a prediction to track it here." />;

  return (
    <Stack spacing={3}>
      <Stack spacing={0.5}><Typography variant="h4">Saved picks</Typography><Typography color="text.secondary">Predictions you have saved for tracking.</Typography></Stack>
      <Stack spacing={1.5}>
        {query.data.picks.map((pick) => (
          <Card key={pick.saved_pick_id} variant="outlined">
            <CardActionArea onClick={() => navigate(`/games/${pick.game_id}`)}>
              <CardContent><Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" spacing={2}>
                <Stack spacing={0.75}><Typography variant="overline" color="text.secondary">{pick.market}</Typography><Typography variant="h5">{pick.selection}</Typography><Typography variant="caption" color="text.secondary">Prediction #{pick.prediction_id}</Typography></Stack>
                <Stack alignItems={{ xs: "flex-start", sm: "flex-end" }} spacing={1}><Typography>{pick.confidence_score == null ? "Not rated" : `${pick.confidence_score.toFixed(1)}% confidence`}</Typography><Chip size="small" label={pick.outcome ?? "Pending"} /></Stack>
              </Stack></CardContent>
            </CardActionArea>
          </Card>
        ))}
      </Stack>
    </Stack>
  );
}
