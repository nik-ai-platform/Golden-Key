import ArrowBackOutlinedIcon from "@mui/icons-material/ArrowBackOutlined";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Grid2 as Grid,
  Stack,
  Typography,
} from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { Link as RouterLink, useParams } from "react-router-dom";

import { EmptyState } from "../components/EmptyState";
import { LoadingState } from "../components/LoadingState";
import { PickMetrics } from "../components/PickMetrics";
import { SavePickButton } from "../components/SavePickButton";
import { getGameDetail } from "../services/productApi";
import type { Prediction } from "../types/product";
import {
  formatAmericanOdds,
  formatProductDate,
} from "../utils/productFormat";

const MARKET_ORDER = ["spread", "moneyline", "total"];

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

function formatScore(value: number): string {
  return Number.isInteger(value) ? value.toFixed(0) : String(value);
}

function marketLabel(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1).toLowerCase();
}

function outcomeColor(
  outcome: string,
): "success" | "error" | "warning" | "default" {
  if (outcome === "WIN") return "success";
  if (outcome === "LOSS") return "error";
  if (outcome === "PUSH") return "warning";
  return "default";
}

function MarketCard({
  prediction,
  isBestPick,
}: {
  prediction: Prediction;
  isBestPick: boolean;
}) {
  return (
    <Card variant="outlined" sx={{ height: "100%", borderRadius: 2 }}>
      <CardContent sx={{ p: { xs: 2.5, md: 3 }, "&:last-child": { pb: { xs: 2.5, md: 3 } } }}>
        <Stack spacing={2.5}>
          <Stack direction="row" justifyContent="space-between" alignItems="center" spacing={1}>
            <Typography variant="overline" color="text.secondary" fontWeight={700}>
              {marketLabel(prediction.market)}
            </Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap justifyContent="flex-end">
              {isBestPick ? <Chip label="Golden Key Best Pick" color="primary" size="small" /> : null}
              {prediction.outcome ? (
                <Chip
                  label={prediction.outcome}
                  color={outcomeColor(prediction.outcome.toUpperCase())}
                  size="small"
                />
              ) : null}
            </Stack>
          </Stack>

          <Box>
            <Typography variant="overline" color="text.secondary">
              Recommended selection
            </Typography>
            <Typography variant="h5" fontWeight={700} sx={{ mt: 0.5, overflowWrap: "anywhere" }}>
              {prediction.display_selection}
            </Typography>
            {prediction.american_odds != null ? (
              <Typography color="text.secondary" sx={{ mt: 0.75 }}>
                American odds {formatAmericanOdds(prediction.american_odds)}
              </Typography>
            ) : null}
          </Box>

          <PickMetrics
            npi={prediction.npi_score}
            confidence={prediction.confidence_score}
            simulationProbability={prediction.simulation_probability}
            projectedEdge={prediction.projected_edge}
            riskLevel={prediction.risk_level}
          />

          {prediction.reasoning ? (
            <Box>
              <Typography variant="subtitle2" fontWeight={700}>
                Why Golden Key Likes This Pick
              </Typography>
              <Typography color="text.secondary" sx={{ mt: 0.75, lineHeight: 1.7 }}>
                {prediction.reasoning}
              </Typography>
            </Box>
          ) : null}

          <SavePickButton predictionId={prediction.prediction_id} />
        </Stack>
      </CardContent>
    </Card>
  );
}

export function ProductGameDetailPage() {
  const { gameId } = useParams();
  const numericGameId = Number(gameId);
  const validGameId = Number.isInteger(numericGameId) && numericGameId > 0;
  const query = useQuery({
    queryKey: ["product", "game", numericGameId],
    queryFn: () => getGameDetail(numericGameId),
    enabled: validGameId,
  });

  if (!validGameId) {
    return <Alert severity="info">Game analysis is unavailable.</Alert>;
  }
  if (query.isLoading) {
    return <LoadingState message="Loading game analysis..." />;
  }
  if (query.isError) {
    return <Alert severity="info">Game analysis is unavailable.</Alert>;
  }

  const game = query.data!;
  const predictions = [...game.predictions].sort(
    (left, right) =>
      MARKET_ORDER.indexOf(left.market.toLowerCase()) -
      MARKET_ORDER.indexOf(right.market.toLowerCase()),
  );
  const bestPrediction = [...predictions].sort(rankPredictions)[0];
  const hasFinalScore =
    game.home_score != null &&
    game.away_score != null &&
    predictions.some((prediction) => prediction.outcome != null);

  return (
    <Stack spacing={3.5}>
      <Button
        component={RouterLink}
        to="/games"
        startIcon={<ArrowBackOutlinedIcon />}
        sx={{ alignSelf: "flex-start" }}
      >
        Back to Games
      </Button>

      <Box>
        <Typography variant="overline" color="primary.main" fontWeight={700}>
          {game.sport}
        </Typography>
        <Typography variant="h4" fontWeight={700} sx={{ mt: 0.5 }}>
          {game.away_team} @ {game.home_team}
        </Typography>
        <Typography color="text.secondary" sx={{ mt: 1 }}>
          {formatProductDate(game.game_date)}
        </Typography>
        {hasFinalScore ? (
          <Typography variant="h6" sx={{ mt: 1.5 }}>
            Final: {game.away_team} {formatScore(game.away_score!)} · {game.home_team} {formatScore(game.home_score!)}
          </Typography>
        ) : null}
      </Box>

      {predictions.length === 0 ? (
        <EmptyState title="No Golden Key predictions are available for this game yet." />
      ) : (
        <Box component="section" aria-label="Golden Key recommendations">
          <Typography variant="h5" fontWeight={700} sx={{ mb: 2 }}>
            Golden Key Recommendations
          </Typography>
          <Grid container spacing={2.5}>
            {predictions.map((prediction) => (
              <Grid key={prediction.prediction_id} size={{ xs: 12, md: 6, xl: 4 }}>
                <MarketCard
                  prediction={prediction}
                  isBestPick={prediction.prediction_id === bestPrediction?.prediction_id}
                />
              </Grid>
            ))}
          </Grid>
        </Box>
      )}
    </Stack>
  );
}