import ArrowForwardOutlinedIcon from "@mui/icons-material/ArrowForwardOutlined";
import DeleteOutlineOutlinedIcon from "@mui/icons-material/DeleteOutlineOutlined";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Divider,
  Grid2 as Grid,
  Stack,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link as RouterLink } from "react-router-dom";

import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { getSavedPicks, removeSavedPrediction } from "../services/productApi";
import type { SavedPick, SavedPicksResponse } from "../types/product";
import {
  formatAmericanOdds,
  formatConfidence,
  formatNpi,
  formatProductDate,
} from "../utils/productFormat";

const savedPicksQueryKey = ["product", "saved-picks"] as const;

function marketLabel(market: string): string {
  const value = market.toLowerCase();

  if (value === "spread") return "Spread";
  if (value === "moneyline") return "Moneyline";
  if (value === "total") return "Total";

  return market;
}

function isSettled(pick: SavedPick): boolean {
  return ["WIN", "LOSS", "PUSH"].includes(pick.outcome?.toUpperCase() ?? "");
}

function outcomeColor(
  outcome: string,
): "success" | "error" | "warning" {
  const value = outcome.toUpperCase();

  if (value === "WIN") return "success";
  if (value === "LOSS") return "error";

  return "warning";
}

function formatScore(score: number): string {
  return Number.isInteger(score) ? score.toFixed(0) : String(score);
}

function RemovePickButton({ predictionId }: { predictionId: number }) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: () => removeSavedPrediction(predictionId),
    onSuccess: async () => {
      queryClient.setQueryData<SavedPicksResponse>(
        savedPicksQueryKey,
        (current) => {
          if (!current) return current;
          const picks = current.picks.filter(
            (pick) => pick.prediction_id !== predictionId,
          );
          return { count: picks.length, picks };
        },
      );
      await queryClient.invalidateQueries({ queryKey: savedPicksQueryKey });
    },
  });

  return (
    <Stack spacing={1} alignItems="flex-start">
      <Button
        type="button"
        color="error"
        variant="outlined"
        startIcon={<DeleteOutlineOutlinedIcon />}
        disabled={mutation.isPending}
        onClick={() => mutation.mutate()}
      >
        {mutation.isPending ? "Removing..." : "Remove Pick"}
      </Button>
      {mutation.isError ? (
        <Alert severity="error">
          Unable to remove this saved pick. Please try again.
        </Alert>
      ) : null}
    </Stack>
  );
}

function SavedPickCard({ pick }: { pick: SavedPick }) {
  const settled = isSettled(pick);
  const hasFinalScore = pick.away_score != null && pick.home_score != null;

  return (
    <Card
      data-testid="saved-pick-card"
      data-prediction-id={pick.prediction_id}
      variant="outlined"
      sx={{ borderRadius: 2, minWidth: 0 }}
    >
      <CardContent
        sx={{
          p: { xs: 2, md: 3 },
          "&:last-child": { pb: { xs: 2, md: 3 } },
        }}
      >
        <Stack spacing={2.5} sx={{ minWidth: 0 }}>
          <Stack
            direction={{ xs: "column", sm: "row" }}
            justifyContent="space-between"
            alignItems={{ sm: "flex-start" }}
            spacing={1.5}
          >
            <Box sx={{ minWidth: 0 }}>
              <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
                <Chip label={pick.sport} size="small" variant="outlined" />
                {settled && pick.outcome ? (
                  <Chip
                    label={pick.outcome.toUpperCase()}
                    size="small"
                    color={outcomeColor(pick.outcome)}
                  />
                ) : null}
              </Stack>

              <Typography
                variant="h6"
                fontWeight={700}
                sx={{ mt: 1, overflowWrap: "anywhere" }}
              >
                {pick.away_team} @ {pick.home_team}
              </Typography>

              <Typography variant="body2" color="text.secondary">
                {formatProductDate(pick.game_date)}
              </Typography>

              {settled && hasFinalScore ? (
                <Typography variant="body2" fontWeight={700} sx={{ mt: 0.5 }}>
                  Final: {formatScore(pick.away_score!)} -{" "}
                  {formatScore(pick.home_score!)}
                </Typography>
              ) : null}
            </Box>

            <Button
              component={RouterLink}
              to={`/games/${pick.game_id}`}
              variant="outlined"
              endIcon={<ArrowForwardOutlinedIcon />}
              sx={{ alignSelf: { xs: "stretch", sm: "flex-start" } }}
            >
              View Game Analysis
            </Button>
          </Stack>

          <Divider />

          <Grid container spacing={2}>
            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <Typography variant="caption" color="text.secondary">
                Market
              </Typography>
              <Typography fontWeight={700}>{marketLabel(pick.market)}</Typography>
            </Grid>

            <Grid size={{ xs: 12, sm: 6, md: 3 }}>
              <Typography variant="caption" color="text.secondary">
                Pick
              </Typography>
              <Typography fontWeight={700} sx={{ overflowWrap: "anywhere" }}>
                {pick.display_selection}
              </Typography>
              {pick.american_odds != null ? (
                <Typography variant="body2" color="text.secondary">
                  Odds {formatAmericanOdds(pick.american_odds)}
                </Typography>
              ) : null}
            </Grid>

            <Grid size={{ xs: 6, sm: 3, md: 2 }}>
              <Typography variant="caption" color="text.secondary">
                NPI
              </Typography>
              <Typography fontWeight={700}>
                {formatNpi(pick.npi_score)}
              </Typography>
            </Grid>

            <Grid size={{ xs: 6, sm: 3, md: 2 }}>
              <Typography variant="caption" color="text.secondary">
                Confidence
              </Typography>
              <Typography fontWeight={700}>
                {formatConfidence(pick.confidence_score)}
              </Typography>
            </Grid>

            {!settled && pick.risk_level ? (
              <Grid size={{ xs: 12, sm: 6, md: 2 }}>
                <Typography variant="caption" color="text.secondary">
                  Risk
                </Typography>
                <Typography fontWeight={700}>{pick.risk_level}</Typography>
              </Grid>
            ) : null}
          </Grid>

          <RemovePickButton predictionId={pick.prediction_id} />
        </Stack>
      </CardContent>
    </Card>
  );
}

export function ProductSavedPicksPage() {
  const query = useQuery({
    queryKey: savedPicksQueryKey,
    queryFn: getSavedPicks,
  });

  if (query.isLoading) {
    return <LoadingState message="Loading saved picks..." />;
  }

  if (query.isError) {
    return (
      <ErrorState
        kind="generic"
        detail="Unable to load saved picks right now."
        onRetry={() => void query.refetch()}
      />
    );
  }

  const picks = query.data?.picks ?? [];
  const pendingPicks = picks
    .filter((pick) => !isSettled(pick))
    .sort(
      (left, right) =>
        new Date(left.game_date).getTime() - new Date(right.game_date).getTime(),
    );
  const settledPicks = picks
    .filter(isSettled)
    .sort(
      (left, right) =>
        new Date(right.game_date).getTime() - new Date(left.game_date).getTime(),
    );

  return (
    <Stack spacing={3}>
      <Box>
        <Typography variant="h4" fontWeight={700}>
          Saved Picks
        </Typography>

        <Typography color="text.secondary" sx={{ mt: 1 }}>
          Track the predictions you selected and see their final results.
        </Typography>
      </Box>

      <Grid container spacing={2}>
        {[
          ["Saved Picks", picks.length, "saved-count"],
          ["Pending", pendingPicks.length, "pending-count"],
          ["Settled", settledPicks.length, "settled-count"],
        ].map(([label, count, testId]) => (
          <Grid key={label} size={{ xs: 12, sm: 4 }}>
            <Card variant="outlined" sx={{ borderRadius: 2 }}>
              <CardContent>
                <Typography variant="body2" color="text.secondary">
                  {label}
                </Typography>
                <Typography
                  data-testid={testId}
                  variant="h4"
                  fontWeight={700}
                  sx={{ mt: 0.5 }}
                >
                  {count}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {!picks.length ? (
        <EmptyState title="You have no saved picks yet." />
      ) : (
        <>
          <Stack component="section" aria-labelledby="pending-picks-heading" spacing={2}>
            <Typography id="pending-picks-heading" variant="h5" fontWeight={700}>
              Pending Picks
            </Typography>
            {pendingPicks.length ? (
              pendingPicks.map((pick) => (
                <SavedPickCard key={pick.saved_pick_id} pick={pick} />
              ))
            ) : (
              <EmptyState title="No pending saved picks." />
            )}
          </Stack>

          <Stack component="section" aria-labelledby="settled-picks-heading" spacing={2}>
            <Typography id="settled-picks-heading" variant="h5" fontWeight={700}>
              Settled Picks
            </Typography>
            {settledPicks.length ? (
              settledPicks.map((pick) => (
                <SavedPickCard key={pick.saved_pick_id} pick={pick} />
              ))
            ) : (
              <EmptyState title="No settled saved picks yet." />
            )}
          </Stack>
        </>
      )}
    </Stack>
  );
}
