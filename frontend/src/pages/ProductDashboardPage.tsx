import {
  Box,
  Card,
  CardContent,
  Divider,
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
import { MetricInfoControl } from "../components/MetricInfoControl";
import { SportsbookGamesBoard } from "../components/SportsbookGamesBoard";
import { TeamAccent } from "../components/TeamAccent";
import { getDailyCard, getUpcomingPredictions } from "../services/productApi";
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

function SectionHeading({
  id,
  children,
  metric,
}: {
  id: string;
  children: string;
  metric?: "npi" | "confidence" | "modelProbability";
}) {
  return (
    <Stack direction="row" alignItems="center" spacing={1.25} sx={{ mb: 1 }}>
      <Typography component="h2" id={id} variant="overline" fontWeight={900} sx={{ flexShrink: 0 }}>
        {children}
      </Typography>
      {metric ? <MetricInfoControl metric={metric} /> : null}
      <Divider sx={{ flexGrow: 1 }} />
    </Stack>
  );
}

function finiteAverage(values: Array<number | null>): number | null {
  const finite = values.filter((value): value is number => value != null && Number.isFinite(value));
  return finite.length > 0 ? finite.reduce((sum, value) => sum + value, 0) / finite.length : null;
}

const panelSx = {
  border: "1px solid var(--gk-border-strong)",
  borderRadius: "var(--gk-radius-sm)",
  backgroundColor: "var(--gk-surface)",
  p: { xs: 1.5, md: 2 },
};

function npiPickSelection(pick: DailyCardPick): string {
  const prediction = pick.prediction;
  const direction = prediction.selection.trim().match(/^(OVER|UNDER)\b/i)?.[1];
  return prediction.market.toLowerCase() === "total" && direction &&
    prediction.line_value != null && Number.isFinite(prediction.line_value)
    ? `${direction.toUpperCase()} ${prediction.line_value}`
    : prediction.display_selection;
}

export function ProductDashboardPage() {
  const [sport, setSport] = useState<SportFilter>("All");
  const query = useQuery({
    queryKey: ["product", "daily-card", sport],
    queryFn: () => getDailyCard(sport === "All" ? undefined : sport),
  });
  const gamesQuery = useQuery({
    queryKey: ["product", "predictions", "upcoming", sport],
    queryFn: () => getUpcomingPredictions(sport === "All" ? undefined : sport),
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
  return (
    <Stack spacing={{ xs: 2, md: 2 }} data-testid="intelligence-dashboard">
      <Stack
        direction={{ xs: "column", md: "row" }}
        alignItems={{ xs: "stretch", md: "center" }}
        justifyContent="space-between"
        spacing={{ xs: 1, sm: 2, md: 3 }}
      >
        <Box>
          <Typography variant="overline" color="primary.main" fontWeight={900}>
            Bear A Hand Sports
          </Typography>
          <Typography variant="h4" fontWeight={850} sx={{ mt: 0.25, fontSize: { xs: "1.75rem", sm: "2.125rem" } }}>
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
            <Box component="section" aria-labelledby="best-bet-heading" sx={panelSx}>
              <SectionHeading id="best-bet-heading">Best Bet</SectionHeading>
              <DailyCardPickCard pick={card.best_bet} prominent presentation="hero" />
            </Box>
          ) : null}

          {marketLeaders.length > 0 ? (
            <Box component="section" aria-labelledby="card-markets-heading" sx={panelSx}>
              <SectionHeading id="card-markets-heading">Market Leaders</SectionHeading>
              <Box
                sx={{
                  display: { xs: "none", md: "grid" },
                  gridTemplateColumns: "minmax(0, 1.5fr) minmax(0, 1.4fr) 90px 110px",
                  px: 1.5,
                  py: 1,
                  border: "1px solid var(--gk-border)",
                  borderBottom: 0,
                  backgroundColor: "var(--gk-surface-soft)",
                }}
              >
                {[
                  { label: "Team / Pick" },
                  { label: "Matchup" },
                  { label: "Odds" },
                  { label: "Model Prob", metric: "modelProbability" as const },
                ].map(({ label, metric }) => (
                  <Stack key={label} direction="row" alignItems="center" spacing={0.25}>
                    <Typography variant="caption" color="text.secondary" fontWeight={850} textTransform="uppercase">
                      {label}
                    </Typography>
                    {metric ? <MetricInfoControl metric={metric} /> : null}
                  </Stack>
                ))}
              </Box>
              <Stack spacing={{ xs: 1, md: 0 }}>
                {marketLeaders.map((pick) => (
                  <DailyCardPickCard key={pick.role} pick={pick} emphasis="featured" presentation="compact" />
                ))}
              </Stack>
            </Box>
          ) : null}

          <Box component="section" aria-label="Model intelligence">
                <Card
                  variant="outlined"
                  sx={{ height: "100%", borderColor: "var(--gk-border-strong)", borderRadius: "var(--gk-radius-sm)", backgroundColor: "var(--gk-surface)" }}
                >
                  <CardContent sx={{ p: { xs: 2, sm: 2.5 }, "&:last-child": { pb: { xs: 2, sm: 2.5 } } }}>
                    <SectionHeading id="model-intelligence-heading">Model Intelligence</SectionHeading>
                    <Stack direction="row" alignItems="center" spacing={0.25}>
                      <Typography variant="overline" color="info.main" fontWeight={900}>
                        NPI Top {npiLeaders.length}
                      </Typography>
                      <MetricInfoControl metric="npi" />
                    </Stack>
                    <Stack divider={<Divider flexItem />} sx={{ mt: 0.5, maxWidth: { md: 640 } }}>
                      {npiLeaders.map((pick, index) => (
                        <Stack key={pick.prediction.prediction_id} direction="row" spacing={1.5} alignItems="center" sx={{ py: 0.85, px: { md: 1 }, "&:nth-of-type(even)": { backgroundColor: { md: "action.hover" } } }}>
                          <Typography color="text.secondary" fontFamily="var(--gk-font-mono)" sx={{ fontSize: { md: "1.0625rem" } }}>0{index + 1}</Typography>
                          <TeamAccent
                            identity={getPredictionTeamIdentity(pick.prediction)}
                            variant="bar"
                            testId="npi-team-accent"
                          />
                          <Box
                            data-testid={`npi-pick-label-${pick.prediction.prediction_id}`}
                            sx={{ flexGrow: 1, minWidth: 0, overflowWrap: "anywhere" }}
                          >
                            {pick.prediction.market.toLowerCase() === "total" ? (
                              <Typography variant="body2" color="text.secondary" sx={{ mb: 0.25, fontSize: { md: "0.9375rem" } }}>
                                {pick.prediction.away_team} @ {pick.prediction.home_team}
                              </Typography>
                            ) : null}
                            <Typography fontFamily="var(--gk-font-mono)" fontWeight={700} sx={{ fontSize: { md: "1.0625rem" } }}>
                              {npiPickSelection(pick)}
                            </Typography>
                          </Box>
                          <Typography color="info.main" fontFamily="var(--gk-font-mono)" fontWeight={800} sx={{ fontSize: { md: "1.0625rem" } }}>
                            {pick.prediction.npi_score.toFixed(1)}
                          </Typography>
                        </Stack>
                      ))}
                    </Stack>
                    <Divider sx={{ my: 1.25 }} />
                    <Stack direction="row" justifyContent="space-between" alignItems="baseline">
                      <Stack direction="row" alignItems="center" spacing={0.25}>
                        <Typography variant="caption" color="text.secondary" fontFamily="var(--gk-font-mono)" textTransform="uppercase">
                          Avg Confidence
                        </Typography>
                        <MetricInfoControl metric="confidence" />
                      </Stack>
                      <Typography color="primary.main" fontFamily="var(--gk-font-mono)" fontWeight={900}>
                        {averageConfidence == null ? "—" : `${averageConfidence.toFixed(1)}%`}
                      </Typography>
                    </Stack>
                  </CardContent>
                </Card>
          </Box>

          {gamesQuery.data && gamesQuery.data.predictions.length > 0 ? (
            <Box component="section" aria-labelledby="upcoming-games-heading" sx={panelSx}>
              <SectionHeading id="upcoming-games-heading">Upcoming Games</SectionHeading>
              <SportsbookGamesBoard
                predictions={gamesQuery.data.predictions}
                recommendedPredictionIds={recommendedPredictionIds}
                maxGames={8}
              />
            </Box>
          ) : null}
        </>
      )}
    </Stack>
  );
}
