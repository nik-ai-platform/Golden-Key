import ArrowForwardOutlinedIcon from "@mui/icons-material/ArrowForwardOutlined";
import {
  Box,
  Button,
  Card,
  CardContent,
  Grid2 as Grid,
  Stack,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link as RouterLink } from "react-router-dom";

import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { ProductPredictionCard } from "../components/ProductPredictionCard";
import { getTodayPredictions } from "../services/productApi";
import type { Prediction, TodayPredictionsResponse } from "../types/product";

const SPORTS = ["NFL", "NBA", "NCAAF", "NCAAB", "WNBA"] as const;
const MARKETS = ["spread", "moneyline", "total"] as const;

type SportFilter = "All" | (typeof SPORTS)[number];

function nullableDescending(left: number | null, right: number | null): number {
  return (right ?? Number.NEGATIVE_INFINITY) -
    (left ?? Number.NEGATIVE_INFINITY);
}

function rankPredictions(left: Prediction, right: Prediction): number {
  return (
    right.npi_score - left.npi_score ||
    nullableDescending(left.confidence_score, right.confidence_score) ||
    nullableDescending(left.projected_edge, right.projected_edge)
  );
}

function marketLabel(market: string): string {
  return market.charAt(0).toUpperCase() + market.slice(1).toLowerCase();
}

function formatGameDate(value: string): string {
  return new Date(value).toLocaleString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

async function getDashboardPredictions(): Promise<TodayPredictionsResponse> {
  const responses = await Promise.all(
    SPORTS.map((sport) => getTodayPredictions(sport)),
  );
  const predictions = Array.from(
    new Map(
      responses
        .flatMap((response) => response.predictions)
        .map((prediction) => [prediction.prediction_id, prediction]),
    ).values(),
  );

  return { sport: null, count: predictions.length, predictions };
}

export function ProductDashboardPage() {
  const [sport, setSport] = useState<SportFilter>("All");
  const query = useQuery({
    queryKey: ["product", "dashboard-predictions"],
    queryFn: getDashboardPredictions,
  });

  const dashboard = useMemo(() => {
    const now = Date.now();
    const ranked = [...(query.data?.predictions ?? [])]
      .filter((prediction) => {
        const gameTime = new Date(prediction.game_date).getTime();
        return gameTime > now && (sport === "All" || prediction.sport === sport);
      })
      .sort(rankPredictions);
    const bestByMarket = MARKETS.map((market) => ({
      market,
      prediction: ranked.find(
        (prediction) => prediction.market.toLowerCase() === market,
      ),
    }));
    const games = new Map<number, Prediction>();

    for (const prediction of ranked) {
      const existing = games.get(prediction.game_id);
      if (!existing || prediction.npi_score > existing.npi_score) {
        games.set(prediction.game_id, prediction);
      }
    }

    return {
      ranked,
      topPicks: ranked.slice(0, 5),
      bestByMarket,
      upcomingGames: Array.from(games.values())
        .sort(
          (left, right) =>
            new Date(left.game_date).getTime() -
            new Date(right.game_date).getTime(),
        )
        .slice(0, 5),
    };
  }, [query.data?.predictions, sport]);

  if (query.isLoading) {
    return <LoadingState message="Loading best picks..." />;
  }

  if (query.isError) {
    return (
      <ErrorState
        kind="network"
        detail="Unable to load predictions right now."
        onRetry={() => void query.refetch()}
      />
    );
  }

  return (
    <Stack spacing={4}>
      <Stack spacing={2}>
        <Box>
          <Typography variant="h4" fontWeight={700}>
            Best Picks Today
          </Typography>
          <Typography color="text.secondary" sx={{ mt: 0.75 }}>
            Golden Key&apos;s strongest upcoming opportunities, ranked by NPI.
          </Typography>
        </Box>

        <ToggleButtonGroup
          exclusive
          value={sport}
          onChange={(_, value: SportFilter | null) => {
            if (value) setSport(value);
          }}
          size="small"
          aria-label="Filter dashboard by sport"
          sx={{ alignSelf: "flex-start", flexWrap: "wrap" }}
        >
          <ToggleButton value="All">All</ToggleButton>
          {SPORTS.map((item) => (
            <ToggleButton key={item} value={item}>
              {item}
            </ToggleButton>
          ))}
        </ToggleButtonGroup>
      </Stack>

      {dashboard.ranked.length === 0 ? (
        <EmptyState title="No upcoming predictions are currently available." />
      ) : (
        <>
          <Box component="section" aria-labelledby="top-picks-heading">
            <Typography id="top-picks-heading" variant="h5" fontWeight={700} sx={{ mb: 2 }}>
              Top Picks
            </Typography>
            <Grid container spacing={2}>
              {dashboard.topPicks.map((prediction, index) => (
                <Grid key={prediction.prediction_id} size={{ xs: 12, lg: 6, xl: 4 }}>
                  <Box data-testid="top-pick" sx={{ height: "100%" }}>
                    <ProductPredictionCard prediction={prediction} rank={index + 1} />
                  </Box>
                </Grid>
              ))}
            </Grid>
          </Box>

          <Box component="section" aria-labelledby="best-market-heading">
            <Typography id="best-market-heading" variant="h5" fontWeight={700} sx={{ mb: 2 }}>
              Best by Market
            </Typography>
            <Grid container spacing={2}>
              {dashboard.bestByMarket.map(({ market, prediction }) => (
                <Grid key={market} size={{ xs: 12, md: 4 }}>
                  <Card variant="outlined" sx={{ height: "100%", borderRadius: 2 }} data-testid={`best-market-${market}`}>
                    <CardContent>
                      <Stack spacing={1.25}>
                        <Typography variant="overline" color="text.secondary" fontWeight={700}>
                          {marketLabel(market)}
                        </Typography>
                        {prediction ? (
                          <>
                            <Typography fontWeight={700}>
                              {prediction.away_team} @ {prediction.home_team}
                            </Typography>
                            <Typography variant="h6">{prediction.display_selection}</Typography>
                            <Typography variant="body2" color="text.secondary">
                              {prediction.sport} · NPI {prediction.npi_score.toFixed(0)}
                            </Typography>
                            <Button
                              component={RouterLink}
                              to={`/games/${prediction.game_id}`}
                              endIcon={<ArrowForwardOutlinedIcon />}
                              sx={{ alignSelf: "flex-start" }}
                            >
                              View game analysis
                            </Button>
                          </>
                        ) : (
                          <Typography color="text.secondary">
                            No {marketLabel(market)} pick available.
                          </Typography>
                        )}
                      </Stack>
                    </CardContent>
                  </Card>
                </Grid>
              ))}
            </Grid>
          </Box>

          <Box component="section" aria-labelledby="upcoming-games-heading">
            <Typography id="upcoming-games-heading" variant="h5" fontWeight={700} sx={{ mb: 2 }}>
              Upcoming Games
            </Typography>
            <Stack spacing={1.25}>
              {dashboard.upcomingGames.map((prediction) => (
                <Card
                  key={prediction.game_id}
                  variant="outlined"
                  data-testid="upcoming-game"
                  data-game-id={prediction.game_id}
                  sx={{ borderRadius: 2 }}
                >
                  <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
                    <Stack
                      direction={{ xs: "column", sm: "row" }}
                      justifyContent="space-between"
                      alignItems={{ sm: "center" }}
                      spacing={1.5}
                    >
                      <Box>
                        <Typography fontWeight={700}>
                          {prediction.away_team} @ {prediction.home_team}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          {prediction.sport} · {formatGameDate(prediction.game_date)} · Best NPI {prediction.npi_score.toFixed(0)}
                        </Typography>
                      </Box>
                      <Button
                        component={RouterLink}
                        to={`/games/${prediction.game_id}`}
                        endIcon={<ArrowForwardOutlinedIcon />}
                      >
                        Game analysis
                      </Button>
                    </Stack>
                  </CardContent>
                </Card>
              ))}
            </Stack>
          </Box>
        </>
      )}
    </Stack>
  );
}