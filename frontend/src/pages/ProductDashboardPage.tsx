import {
  Box,
  Card,
  CardContent,
  Divider,
  Grid2 as Grid,
  Stack,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { DailyCardPickCard } from "../components/DailyCardPickCard";
import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { SportsbookGamesBoard } from "../components/SportsbookGamesBoard";
import { TeamAccent } from "../components/TeamAccent";
import { getDailyCard, getTodayPredictions } from "../services/productApi";
import type { DailyCardPick } from "../types/product";
import { getPredictionTeamIdentity } from "../utils/teamIdentity";

const SPORTS = ["NFL", "NBA", "NCAAF", "NCAAB", "WNBA"] as const;
type SportFilter = "All" | (typeof SPORTS)[number];

function slateLabel(slateDate: string): string {
  const today = new Date().toISOString().slice(0, 10);
  if (slateDate === today) return "Today's Card";
  return `Next Slate — ${new Date(`${slateDate}T00:00:00Z`).toLocaleDateString(undefined, {
    month: "long",
    day: "numeric",
    timeZone: "UTC",
  })}`;
}

function SectionHeading({ id, children }: { id: string; children: string }) {
  return (
    <Stack direction="row" alignItems="center" spacing={1.25} sx={{ mb: 1 }}>
      <Typography component="h2" id={id} variant="overline" fontWeight={900} sx={{ flexShrink: 0 }}>
        {children}
      </Typography>
      <Divider sx={{ flexGrow: 1 }} />
    </Stack>
  );
}

function finiteAverage(values: Array<number | null>): number | null {
  const finite = values.filter((value): value is number => value != null && Number.isFinite(value));
  return finite.length > 0 ? finite.reduce((sum, value) => sum + value, 0) / finite.length : null;
}

export function ProductDashboardPage() {
  const [sport, setSport] = useState<SportFilter>("All");
  const query = useQuery({
    queryKey: ["product", "daily-card", sport],
    queryFn: () => getDailyCard(sport === "All" ? undefined : sport),
  });
  const gamesQuery = useQuery({
    queryKey: ["product", "predictions", "today", sport],
    queryFn: () => getTodayPredictions(sport === "All" ? undefined : sport),
  });

  if (query.isLoading) {
    return <LoadingState message="Building today's card..." />;
  }

  if (query.isError) {
    return (
      <ErrorState
        kind="network"
        detail="Unable to load today's card right now."
        onRetry={() => void query.refetch()}
      />
    );
  }

  const card = query.data;
  const allPicks = card
    ? [card.best_bet, ...card.featured_picks, ...card.next_best].filter(
        (pick): pick is DailyCardPick => pick != null,
      )
    : [];
  const uniquePicks = allPicks.filter(
    (pick, index, picks) =>
      picks.findIndex((candidate) => candidate.prediction.prediction_id === pick.prediction.prediction_id) === index,
  );
  const recommendedPredictionIds = new Set(allPicks.map((pick) => pick.prediction.prediction_id));
  const marketLeaders = card?.featured_picks.filter((pick) =>
    ["TOP_SPREAD", "TOP_MONEYLINE", "TOP_TOTAL"].includes(pick.role),
  ) ?? [];
  const npiLeaders = [...uniquePicks]
    .filter((pick) => Number.isFinite(pick.prediction.npi_score))
    .sort((left, right) => right.prediction.npi_score - left.prediction.npi_score)
    .slice(0, 5);
  const averageConfidence = finiteAverage(uniquePicks.map((pick) => pick.prediction.confidence_score));
  const measuredEdges = uniquePicks
    .map((pick) => pick.prediction.projected_edge)
    .filter((edge): edge is number => edge != null && Number.isFinite(edge));
  const edgeCounts = measuredEdges.reduce(
    (counts, edge) => {
      if (edge > 0) counts.positive += 1;
      else if (edge < 0) counts.negative += 1;
      else counts.none += 1;
      return counts;
    },
    { positive: 0, negative: 0, none: 0 },
  );
  const edgePercentage = (count: number) =>
    measuredEdges.length > 0 ? (count / measuredEdges.length) * 100 : 0;
  const positiveEdge = edgePercentage(edgeCounts.positive);
  const negativeEdge = edgePercentage(edgeCounts.negative);
  const noEdge = edgePercentage(edgeCounts.none);

  return (
    <Stack spacing={{ xs: 3, md: 2 }} data-testid="intelligence-dashboard">
      <Stack
        direction={{ xs: "column", md: "row" }}
        alignItems={{ xs: "stretch", md: "center" }}
        justifyContent="space-between"
        spacing={{ xs: 2, md: 3 }}
      >
        <Box>
          <Typography variant="overline" color="primary.main" fontWeight={900}>
            Golden Key
          </Typography>
          <Typography variant="h4" fontWeight={850} sx={{ mt: 0.25 }}>
            Today&apos;s Intelligence
          </Typography>
          <Typography color="text.secondary" sx={{ mt: 0.5 }}>
            {card ? slateLabel(card.slate_date) : "Daily model intelligence"}
          </Typography>
        </Box>

        <ToggleButtonGroup
          exclusive
          value={sport}
          onChange={(_, value: SportFilter | null) => {
            if (value) setSport(value);
          }}
          size="small"
          aria-label="Filter daily card by sport"
          sx={{
            alignSelf: { xs: "stretch", md: "center" },
            width: { md: "auto" },
            maxWidth: "100%",
            overflowX: "auto",
            "& .MuiToggleButton-root": { flex: { xs: "0 0 auto", sm: "0 1 auto" } },
          }}
        >
          <ToggleButton value="All">All</ToggleButton>
          {SPORTS.map((item) => (
            <ToggleButton key={item} value={item}>
              {item}
            </ToggleButton>
          ))}
        </ToggleButtonGroup>
      </Stack>

      {!card || card.count === 0 ? (
        <EmptyState title="No upcoming predictions are currently available." />
      ) : (
        <>
          {card.best_bet ? (
            <Box component="section" aria-labelledby="best-bet-heading">
              <SectionHeading id="best-bet-heading">Best Bet</SectionHeading>
              <DailyCardPickCard pick={card.best_bet} prominent presentation="hero" />
            </Box>
          ) : null}

          {marketLeaders.length > 0 ? (
            <Box component="section" aria-labelledby="card-markets-heading">
              <SectionHeading id="card-markets-heading">Market Leaders</SectionHeading>
              <Box
                sx={{
                  display: { xs: "none", md: "grid" },
                  gridTemplateColumns: "minmax(190px, 1.5fr) minmax(220px, 1.4fr) 90px 110px 90px",
                  px: 1.5,
                  py: 0.75,
                  border: "1px solid var(--gk-border)",
                  borderBottom: 0,
                  backgroundColor: "rgba(0, 0, 0, 0.22)",
                }}
              >
                {['Team / Pick', 'Matchup', 'Odds', 'Win Prob', 'Edge'].map((label) => (
                  <Typography key={label} variant="caption" color="text.secondary" fontWeight={850} textTransform="uppercase">
                    {label}
                  </Typography>
                ))}
              </Box>
              <Stack spacing={{ xs: 1, md: 0 }}>
                {marketLeaders.map((pick) => (
                  <DailyCardPickCard key={pick.role} pick={pick} emphasis="featured" presentation="compact" />
                ))}
              </Stack>
            </Box>
          ) : null}

          <Box component="section" aria-label="Prediction and model intelligence">
            <Grid container spacing={1.5}>
              <Grid size={{ xs: 12, md: 6 }}>
                <Card variant="outlined" sx={{ height: "100%", borderRadius: "var(--gk-radius-sm)" }}>
                  <CardContent sx={{ p: { xs: 2, sm: 2.5 }, "&:last-child": { pb: { xs: 2, sm: 2.5 } } }}>
                    <SectionHeading id="prediction-summary-heading">Prediction Summary</SectionHeading>
                    <Stack direction={{ xs: "column", sm: "row" }} alignItems="center" spacing={{ xs: 2.5, sm: 4 }} sx={{ pt: 1 }}>
                      <Box
                        role="img"
                        aria-label={`${positiveEdge.toFixed(0)}% positive edge`}
                        sx={{
                          width: 164,
                          height: 164,
                          flex: "0 0 164px",
                          borderRadius: "50%",
                          display: "grid",
                          placeItems: "center",
                          background: `conic-gradient(var(--gk-gold) 0 ${positiveEdge}%, #d15f57 ${positiveEdge}% ${positiveEdge + negativeEdge}%, var(--gk-border-strong) ${positiveEdge + negativeEdge}% 100%)`,
                          position: "relative",
                          "&::before": {
                            content: '""',
                            position: "absolute",
                            inset: 15,
                            borderRadius: "50%",
                            backgroundColor: "var(--gk-surface)",
                            border: "1px solid var(--gk-border)",
                          },
                        }}
                      >
                        <Box sx={{ position: "relative", textAlign: "center" }}>
                          <Typography variant="h4" fontWeight={900}>{positiveEdge.toFixed(0)}%</Typography>
                          <Typography variant="caption" color="primary.main" fontWeight={900}>POS EDGE</Typography>
                        </Box>
                      </Box>
                      <Stack spacing={1.25} sx={{ width: "100%", minWidth: 0 }}>
                        {[
                          ["Positive", positiveEdge, "var(--gk-gold)"],
                          ["Negative", negativeEdge, "#d15f57"],
                          ["No Edge", noEdge, "var(--gk-border-strong)"],
                        ].map(([label, value, color]) => (
                          <Stack key={label as string} direction="row" alignItems="center" spacing={1}>
                            <Box sx={{ width: 8, height: 8, backgroundColor: color, flexShrink: 0 }} />
                            <Typography color="text.secondary" sx={{ flexGrow: 1 }}>{label}</Typography>
                            <Typography fontWeight={850}>{(value as number).toFixed(0)}%</Typography>
                          </Stack>
                        ))}
                        <Typography variant="caption" color="text.secondary" sx={{ pt: 0.5 }}>
                          {measuredEdges.length} measured signals
                        </Typography>
                      </Stack>
                    </Stack>
                  </CardContent>
                </Card>
              </Grid>
              <Grid size={{ xs: 12, md: 6 }}>
                <Card
                  variant="outlined"
                  sx={{ height: "100%", borderRadius: "var(--gk-radius-sm)", backgroundColor: "var(--gk-surface-soft)" }}
                >
                  <CardContent sx={{ p: { xs: 2, sm: 2.5 }, "&:last-child": { pb: { xs: 2, sm: 2.5 } } }}>
                    <SectionHeading id="model-intelligence-heading">Model Intelligence</SectionHeading>
                    <Typography variant="overline" color="info.main" fontWeight={900}>
                      NPI Top {npiLeaders.length}
                    </Typography>
                    <Stack divider={<Divider flexItem />} sx={{ mt: 0.5 }}>
                      {npiLeaders.map((pick, index) => (
                        <Stack key={pick.prediction.prediction_id} direction="row" spacing={1.5} alignItems="center" sx={{ py: 0.85 }}>
                          <Typography color="text.secondary" fontFamily="monospace">0{index + 1}</Typography>
                          <TeamAccent
                            identity={getPredictionTeamIdentity(pick.prediction)}
                            variant="bar"
                            testId="npi-team-accent"
                          />
                          <Typography fontFamily="monospace" fontWeight={700} sx={{ flexGrow: 1, minWidth: 0 }} noWrap>
                            {pick.prediction.display_selection}
                          </Typography>
                          <Typography color="info.main" fontFamily="monospace" fontWeight={800}>
                            {pick.prediction.npi_score.toFixed(1)}
                          </Typography>
                        </Stack>
                      ))}
                    </Stack>
                    <Divider sx={{ my: 1.25 }} />
                    <Stack direction="row" justifyContent="space-between" alignItems="baseline">
                      <Typography variant="caption" color="text.secondary" fontFamily="monospace" textTransform="uppercase">
                        Avg Confidence
                      </Typography>
                      <Typography color="primary.main" fontFamily="monospace" fontWeight={900}>
                        {averageConfidence == null ? "—" : `${averageConfidence.toFixed(1)}%`}
                      </Typography>
                    </Stack>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          </Box>

          {gamesQuery.data && gamesQuery.data.predictions.length > 0 ? (
            <Box component="section" aria-labelledby="todays-games-heading">
              <SectionHeading id="todays-games-heading">Today&apos;s Games</SectionHeading>
              <SportsbookGamesBoard
                predictions={gamesQuery.data.predictions}
                recommendedPredictionIds={recommendedPredictionIds}
              />
            </Box>
          ) : null}
        </>
      )}
    </Stack>
  );
}
