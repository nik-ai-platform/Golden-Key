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
import { getDailyCard } from "../services/productApi";
import type { DailyCardPick } from "../types/product";

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
    <Stack direction="row" alignItems="center" spacing={1.5} sx={{ mb: 2 }}>
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
  const gamePicks = [...allPicks]
    .sort((left, right) => right.ranking_score - left.ranking_score)
    .filter(
      (pick, index, picks) =>
        picks.findIndex((candidate) => candidate.prediction.game_id === pick.prediction.game_id) === index,
    );
  const marketLeaders = card?.featured_picks.filter((pick) =>
    ["TOP_SPREAD", "TOP_MONEYLINE", "TOP_TOTAL"].includes(pick.role),
  ) ?? [];
  const npiLeaders = [...uniquePicks]
    .sort((left, right) => right.prediction.npi_score - left.prediction.npi_score)
    .slice(0, 3);
  const averageConfidence = finiteAverage(uniquePicks.map((pick) => pick.prediction.confidence_score));
  const averageEdge = finiteAverage(uniquePicks.map((pick) => pick.prediction.projected_edge));

  return (
    <Stack spacing={{ xs: 4, md: 6 }} data-testid="intelligence-dashboard">
      <Stack spacing={2.5}>
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
            alignSelf: "stretch",
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
              <Grid container spacing={2}>
                {marketLeaders.map((pick) => (
                  <Grid key={pick.role} size={{ xs: 12, md: 4 }}>
                    <DailyCardPickCard pick={pick} emphasis="featured" presentation="compact" />
                  </Grid>
                ))}
              </Grid>
            </Box>
          ) : null}

          <Box component="section" aria-labelledby="model-intelligence-heading">
            <SectionHeading id="model-intelligence-heading">Model Intelligence</SectionHeading>
            <Grid container spacing={2}>
              <Grid size={{ xs: 12, md: 7 }}>
                <Card variant="outlined" sx={{ height: "100%", borderRadius: "var(--gk-radius-sm)" }}>
                  <CardContent sx={{ p: { xs: 2, sm: 2.5 }, "&:last-child": { pb: { xs: 2, sm: 2.5 } } }}>
                    <Typography variant="overline" color="text.secondary" fontWeight={900}>
                      Prediction Summary
                    </Typography>
                    <Typography variant="h5" sx={{ mt: 0.5 }}>
                      {uniquePicks.length} ranked signals
                    </Typography>
                    <Grid container spacing={{ xs: 1, sm: 1.5 }} sx={{ mt: 1 }}>
                      {[
                        ["Markets", new Set(uniquePicks.map((pick) => pick.prediction.market)).size.toString()],
                        ["Avg. confidence", averageConfidence == null ? "—" : `${averageConfidence.toFixed(1)}%`],
                        ["Avg. edge", averageEdge == null ? "—" : `${averageEdge > 0 ? "+" : ""}${averageEdge.toFixed(1)}%`],
                      ].map(([label, value]) => (
                        <Grid key={label} size={{ xs: 4 }}>
                          <Box sx={{ backgroundColor: "var(--gk-analytics-soft)", p: { xs: 1, sm: 1.5 }, minHeight: 76 }}>
                            <Typography variant="caption" color="text.secondary" fontWeight={800}>{label}</Typography>
                            <Typography variant="h6" color={label === "Avg. edge" ? "info.main" : "text.primary"}>{value}</Typography>
                          </Box>
                        </Grid>
                      ))}
                    </Grid>
                  </CardContent>
                </Card>
              </Grid>
              <Grid size={{ xs: 12, md: 5 }}>
                <Card
                  variant="outlined"
                  sx={{ height: "100%", borderRadius: "var(--gk-radius-sm)", backgroundColor: "var(--gk-surface-soft)" }}
                >
                  <CardContent sx={{ p: { xs: 2, sm: 2.5 }, "&:last-child": { pb: { xs: 2, sm: 2.5 } } }}>
                    <Typography variant="overline" color="info.main" fontWeight={900}>
                      NPI Leaders
                    </Typography>
                    <Stack divider={<Divider flexItem />} sx={{ mt: 1 }}>
                      {npiLeaders.map((pick, index) => (
                        <Stack key={pick.prediction.prediction_id} direction="row" spacing={1.5} alignItems="center" sx={{ py: 1 }}>
                          <Typography color="text.secondary" fontFamily="monospace">0{index + 1}</Typography>
                          <Typography fontFamily="monospace" fontWeight={700} sx={{ flexGrow: 1, minWidth: 0 }} noWrap>
                            {pick.prediction.display_selection}
                          </Typography>
                          <Typography color="info.main" fontFamily="monospace" fontWeight={800}>
                            {Math.round(pick.prediction.npi_score)}
                          </Typography>
                        </Stack>
                      ))}
                    </Stack>
                  </CardContent>
                </Card>
              </Grid>
            </Grid>
          </Box>

          {gamePicks.length > 0 ? (
            <Box component="section" aria-labelledby="todays-games-heading">
              <SectionHeading id="todays-games-heading">Today&apos;s Games</SectionHeading>
              <Stack spacing={1.5}>
                {gamePicks.map((pick) => (
                  <Box
                    key={pick.prediction.prediction_id}
                    data-testid={pick.role === "NEXT_BEST" ? "next-best-pick" : undefined}
                  >
                    <DailyCardPickCard pick={pick} presentation="row" />
                  </Box>
                ))}
              </Stack>
            </Box>
          ) : null}
        </>
      )}
    </Stack>
  );
}
