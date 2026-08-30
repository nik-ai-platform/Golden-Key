import {
  Box,
  Card,
  CardContent,
  Chip,
  Grid2 as Grid,
  Stack,
  Typography,
} from "@mui/material";
import { useQuery } from "@tanstack/react-query";

import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { getPerformance } from "../services/productApi";
import type {
  PerformanceBreakdown,
  RecentPerformanceResult,
} from "../types/product";
import { formatNpi, formatProductDate } from "../utils/productFormat";

const marketOrder = ["spread", "moneyline", "total"];
const sportOrder = ["NFL", "NBA", "NCAAF", "NCAAB", "WNBA"];

function winRate(wins: number, losses: number): string {
  const decisions = wins + losses;
  return decisions ? `${(wins / decisions * 100).toFixed(1)}%` : "—";
}

function titleCase(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1).toLowerCase();
}

function formatScore(score: number): string {
  return Number.isInteger(score) ? score.toFixed(0) : String(score);
}

function BreakdownCard({
  breakdown,
  recordOnly = false,
}: {
  breakdown: PerformanceBreakdown;
  recordOnly?: boolean;
}) {
  return (
    <Card variant="outlined" sx={{ borderRadius: 2, height: "100%", minWidth: 0 }}>
      <CardContent>
        <Typography variant="h6" fontWeight={700}>
          {marketOrder.includes(breakdown.name.toLowerCase())
            ? titleCase(breakdown.name)
            : breakdown.name.toUpperCase()}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          Settled
        </Typography>
        <Typography variant="h5" fontWeight={700}>
          {breakdown.settled}
        </Typography>
        {recordOnly ? (
          <Typography sx={{ mt: 1 }}>
            Record <strong>{breakdown.wins}-{breakdown.losses}-{breakdown.pushes}</strong>
          </Typography>
        ) : (
          <Typography sx={{ mt: 1 }}>
            {breakdown.wins} W · {breakdown.losses} L · {breakdown.pushes} P
          </Typography>
        )}
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
          Win Rate {winRate(breakdown.wins, breakdown.losses)}
        </Typography>
      </CardContent>
    </Card>
  );
}

function outcomeColor(outcome: RecentPerformanceResult["outcome"]) {
  if (outcome === "WIN") return "success";
  if (outcome === "LOSS") return "error";
  return "warning";
}

function RecentResultCard({ result }: { result: RecentPerformanceResult }) {
  const hasFinalScore = result.away_score != null && result.home_score != null;

  return (
    <Card
      data-testid="recent-result"
      data-prediction-id={result.prediction_id}
      variant="outlined"
      sx={{ borderRadius: 2, minWidth: 0 }}
    >
      <CardContent>
        <Stack
          direction={{ xs: "column", sm: "row" }}
          justifyContent="space-between"
          alignItems={{ sm: "flex-start" }}
          spacing={2}
        >
          <Box sx={{ minWidth: 0 }}>
            <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
              <Chip label={result.sport} size="small" variant="outlined" />
              <Chip
                label={result.outcome}
                size="small"
                color={outcomeColor(result.outcome)}
              />
            </Stack>
            <Typography
              variant="h6"
              fontWeight={700}
              sx={{ mt: 1, overflowWrap: "anywhere" }}
            >
              {result.away_team} @ {result.home_team}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {formatProductDate(result.game_date)}
            </Typography>
            {hasFinalScore ? (
              <Typography variant="body2" fontWeight={700} sx={{ mt: 0.5 }}>
                Final: {formatScore(result.away_score!)} - {formatScore(result.home_score!)}
              </Typography>
            ) : null}
          </Box>

          <Box sx={{ minWidth: { sm: 240 }, maxWidth: "100%" }}>
            <Typography variant="caption" color="text.secondary">
              {titleCase(result.market)}
            </Typography>
            <Typography fontWeight={700} sx={{ overflowWrap: "anywhere" }}>
              {result.display_selection}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              NPI {formatNpi(result.npi_score)}
            </Typography>
          </Box>
        </Stack>
      </CardContent>
    </Card>
  );
}

export function ProductPerformancePage() {
  const query = useQuery({
    queryKey: ["product", "performance"],
    queryFn: getPerformance,
  });

  if (query.isLoading) {
    return <LoadingState message="Loading performance..." />;
  }

  if (query.isError) {
    return (
      <ErrorState
        kind="network"
        detail="Unable to load performance right now."
        onRetry={() => void query.refetch()}
      />
    );
  }

  const performance = query.data!;
  const markets = performance.market_performance
    .filter((item) => marketOrder.includes(item.name.toLowerCase()))
    .sort(
      (left, right) =>
        marketOrder.indexOf(left.name.toLowerCase()) -
        marketOrder.indexOf(right.name.toLowerCase()),
    );
  const sports = performance.sport_performance
    .filter((item) => sportOrder.includes(item.name.toUpperCase()))
    .sort(
      (left, right) =>
        sportOrder.indexOf(left.name.toUpperCase()) -
        sportOrder.indexOf(right.name.toUpperCase()),
    );
  const recentResults = [...performance.recent_results]
    .sort(
      (left, right) =>
        new Date(right.game_date).getTime() - new Date(left.game_date).getTime(),
    )
    .slice(0, 10);

  return (
    <Stack spacing={4}>
      <Box>
        <Typography variant="h4" fontWeight={700}>
          Performance
        </Typography>

        <Typography color="text.secondary" sx={{ mt: 1 }}>
          Results from settled Golden Key predictions.
        </Typography>
      </Box>

      {!performance.total_predictions ? (
        <EmptyState title="No settled Golden Key predictions are available yet." />
      ) : (
        <>
          <Grid container spacing={2}>
            {[
              ["Total Settled", performance.total_predictions],
              ["Wins", performance.wins],
              ["Losses", performance.losses],
              ["Pushes", performance.pushes],
              ["Win Rate", winRate(performance.wins, performance.losses)],
            ].map(([label, value]) => (
              <Grid key={label} size={{ xs: 12, sm: 6, md: 2.4 }}>
                <Card variant="outlined" sx={{ borderRadius: 2, height: "100%" }}>
                  <CardContent>
                    <Typography variant="body2" color="text.secondary">
                      {label}
                    </Typography>
                    <Typography variant="h4" fontWeight={700} sx={{ mt: 0.5 }}>
                      {value}
                    </Typography>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>

          {markets.length ? (
            <Stack component="section" aria-labelledby="market-performance" spacing={2}>
              <Typography id="market-performance" variant="h5" fontWeight={700}>
                Market Performance
              </Typography>
              <Grid container spacing={2}>
                {markets.map((market) => (
                  <Grid key={market.name} size={{ xs: 12, md: 4 }}>
                    <BreakdownCard breakdown={market} />
                  </Grid>
                ))}
              </Grid>
            </Stack>
          ) : null}

          {sports.length ? (
            <Stack component="section" aria-labelledby="sport-performance" spacing={2}>
              <Typography id="sport-performance" variant="h5" fontWeight={700}>
                Sport Performance
              </Typography>
              <Grid container spacing={2}>
                {sports.map((sport) => (
                  <Grid key={sport.name} size={{ xs: 12, sm: 6, md: 4 }}>
                    <BreakdownCard breakdown={sport} recordOnly />
                  </Grid>
                ))}
              </Grid>
            </Stack>
          ) : null}

          {recentResults.length ? (
            <Stack component="section" aria-labelledby="recent-results" spacing={2}>
              <Typography id="recent-results" variant="h5" fontWeight={700}>
                Recent Results
              </Typography>
              {recentResults.map((result) => (
                <RecentResultCard key={result.prediction_id} result={result} />
              ))}
            </Stack>
          ) : null}
        </>
      )}
    </Stack>
  );
}
