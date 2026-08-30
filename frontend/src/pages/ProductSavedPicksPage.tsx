import ArrowForwardOutlinedIcon from "@mui/icons-material/ArrowForwardOutlined";
import {
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
import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { useNavigate } from "react-router-dom";

import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { getSavedPicks } from "../services/productApi";
import type { SavedPick } from "../types/product";

function marketLabel(market: string): string {
  const value = market.toLowerCase();

  if (value === "spread") return "Spread";
  if (value === "moneyline") return "Moneyline";
  if (value === "total") return "Total";

  return market;
}

function marketOrder(market: string): number {
  const value = market.toLowerCase();

  if (value === "spread") return 1;
  if (value === "moneyline") return 2;
  if (value === "total") return 3;

  return 99;
}

function outcomeLabel(outcome: string | null): string {
  if (!outcome) return "Pending";

  const value = outcome.toLowerCase();

  if (value === "win") return "Win";
  if (value === "loss") return "Loss";
  if (value === "push") return "Push";

  return outcome;
}

function outcomeColor(
  outcome: string | null,
): "success" | "error" | "warning" | "default" {
  if (!outcome) return "default";

  const value = outcome.toLowerCase();

  if (value === "win") return "success";
  if (value === "loss") return "error";
  if (value === "push") return "warning";

  return "default";
}

export function ProductSavedPicksPage() {
  const navigate = useNavigate();

  const query = useQuery({
    queryKey: ["product", "saved-picks"],
    queryFn: getSavedPicks,
  });

  const games = useMemo(() => {
    const grouped = new Map<number, SavedPick[]>();

    for (const pick of query.data?.picks ?? []) {
      const existing = grouped.get(pick.game_id) ?? [];
      existing.push(pick);
      grouped.set(pick.game_id, existing);
    }

    return Array.from(grouped.entries())
      .map(([gameId, picks]) => ({
        gameId,
        picks: [...picks].sort(
          (a, b) => marketOrder(a.market) - marketOrder(b.market),
        ),
      }))
      .sort((a, b) => b.gameId - a.gameId);
  }, [query.data?.picks]);

  if (query.isLoading) {
    return <LoadingState message="Loading saved picks..." />;
  }

  if (query.isError) {
    return (
      <ErrorState
        kind="generic"
        detail="Unable to load saved picks."
        onRetry={() => void query.refetch()}
      />
    );
  }

  const picks = query.data?.picks ?? [];

  const pendingCount = picks.filter((pick) => !pick.outcome).length;
  const winCount = picks.filter(
    (pick) => pick.outcome?.toLowerCase() === "win",
  ).length;
  const lossCount = picks.filter(
    (pick) => pick.outcome?.toLowerCase() === "loss",
  ).length;

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

      {picks.length ? (
        <>
          <Grid container spacing={2}>
            <Grid size={{ xs: 12, sm: 4 }}>
              <Card variant="outlined" sx={{ borderRadius: 2 }}>
                <CardContent>
                  <Typography variant="body2" color="text.secondary">
                    Saved
                  </Typography>

                  <Typography variant="h4" fontWeight={700} sx={{ mt: 0.5 }}>
                    {picks.length}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>

            <Grid size={{ xs: 12, sm: 4 }}>
              <Card variant="outlined" sx={{ borderRadius: 2 }}>
                <CardContent>
                  <Typography variant="body2" color="text.secondary">
                    Pending
                  </Typography>

                  <Typography variant="h4" fontWeight={700} sx={{ mt: 0.5 }}>
                    {pendingCount}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>

            <Grid size={{ xs: 12, sm: 4 }}>
              <Card variant="outlined" sx={{ borderRadius: 2 }}>
                <CardContent>
                  <Typography variant="body2" color="text.secondary">
                    Record
                  </Typography>

                  <Typography variant="h4" fontWeight={700} sx={{ mt: 0.5 }}>
                    {winCount}-{lossCount}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>

          <Stack spacing={2}>
            {games.map(({ gameId, picks: gamePicks }) => (
              <Card
                key={gameId}
                variant="outlined"
                sx={{
                  borderRadius: 3,
                  overflow: "hidden",
                }}
              >
                <CardContent
                  sx={{
                    p: { xs: 2, md: 3 },
                    "&:last-child": {
                      pb: { xs: 2, md: 3 },
                    },
                  }}
                >
                  <Stack spacing={2.5}>
                    <Stack
                      direction={{ xs: "column", sm: "row" }}
                      justifyContent="space-between"
                      alignItems={{ sm: "center" }}
                      spacing={1.5}
                    >
                      <Box>
                        <Typography variant="overline" color="text.secondary">
                          Saved matchup
                        </Typography>

                        <Typography variant="h6" fontWeight={700}>
                          Game #{gameId}
                        </Typography>

                        <Typography variant="body2" color="text.secondary">
                          {gamePicks.length} saved{" "}
                          {gamePicks.length === 1 ? "market" : "markets"}
                        </Typography>
                      </Box>

                      <Button
                        variant="outlined"
                        endIcon={<ArrowForwardOutlinedIcon />}
                        onClick={() => navigate(`/games/${gameId}`)}
                      >
                        View Game
                      </Button>
                    </Stack>

                    <Divider />

                    <Grid container spacing={2}>
                      {gamePicks.map((pick) => (
                        <Grid
                          key={pick.saved_pick_id}
                          size={{ xs: 12, md: 4 }}
                        >
                          <Box
                            sx={{
                              border: "1px solid",
                              borderColor: "divider",
                              borderRadius: 2,
                              p: 2,
                              height: "100%",
                            }}
                          >
                            <Stack spacing={1.5}>
                              <Stack
                                direction="row"
                                justifyContent="space-between"
                                alignItems="center"
                                spacing={1}
                              >
                                <Typography
                                  variant="overline"
                                  color="text.secondary"
                                  fontWeight={700}
                                >
                                  {marketLabel(pick.market)}
                                </Typography>

                                <Chip
                                  size="small"
                                  color={outcomeColor(pick.outcome)}
                                  label={outcomeLabel(pick.outcome)}
                                />
                              </Stack>

                              <Typography variant="h6" fontWeight={700}>
                                {pick.selection}
                              </Typography>

                              <Box>
                                <Typography
                                  variant="caption"
                                  color="text.secondary"
                                >
                                  Confidence
                                </Typography>

                                <Typography fontWeight={700}>
                                  {pick.confidence_score == null
                                    ? "Not rated"
                                    : `${pick.confidence_score.toFixed(1)}%`}
                                </Typography>
                              </Box>
                            </Stack>
                          </Box>
                        </Grid>
                      ))}
                    </Grid>
                  </Stack>
                </CardContent>
              </Card>
            ))}
          </Stack>
        </>
      ) : (
        <EmptyState
          title="No saved picks"
          description="Choose a Spread, Moneyline, or Total prediction from Games and save it to track the result here."
        />
      )}
    </Stack>
  );
}
