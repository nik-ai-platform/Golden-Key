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
import { MetricInfoControl } from "../components/MetricInfoControl";
import { PickMetrics } from "../components/PickMetrics";
import { SavePickButton } from "../components/SavePickButton";
import {
  modelProbabilityMarketNote,
  npiMarketNote,
  predictionMetricEducation,
  projectedEdgeMarketNote,
} from "../data/predictionMetricEducation";
import { getGameDetail } from "../services/productApi";
import type { Prediction } from "../types/product";
import {
  formatAmericanOdds,
  formatConfidence,
  formatNpi,
  formatProductDate,
  formatProjectedEdge,
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

function displayRisk(value: string | null): string {
  if (!value) return "Not rated";
  const normalized = value.toLowerCase();
  return normalized.charAt(0).toUpperCase() + normalized.slice(1);
}

function UnderstandingMetric({
  label,
  value,
  explanation,
  metric,
  market,
}: {
  label: string;
  value: string;
  explanation: string;
  metric: "npi" | "confidence" | "projectedEdge" | "modelProbability";
  market: string;
}) {
  return (
    <Box sx={{ minWidth: 0 }}>
      <Stack direction="row" alignItems="center" spacing={0.25}>
        <Typography variant="overline" color="text.secondary" fontWeight={800}>
          {label}
        </Typography>
        <MetricInfoControl metric={metric} market={market} />
      </Stack>
      <Typography fontWeight={850}>{value}</Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, lineHeight: 1.6 }}>
        {explanation}
      </Typography>
    </Box>
  );
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
            {prediction.sportsbook ? (
              <Typography variant="body2">
                Sportsbook: {prediction.sportsbook}
              </Typography>
            ) : null}
            {prediction.odds_observed_at ? (
              <Typography variant="body2">
                Observed: {new Date(prediction.odds_observed_at).toLocaleString()}
              </Typography>
            ) : null}
          </Box>

          <PickMetrics
            npi={prediction.npi_score}
            confidence={prediction.confidence_score}
            simulationProbability={prediction.simulation_probability}
            projectedEdge={prediction.projected_edge}
            riskLevel={prediction.risk_level}
            market={prediction.market}
          />

          <Box
            component="section"
            aria-label={`Understanding this ${prediction.market} pick`}
            sx={{ borderTop: "1px solid", borderColor: "divider", pt: 2.5 }}
          >
            <Typography variant="h6" fontWeight={750}>
              Understanding This Pick
            </Typography>
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: { xs: "minmax(0, 1fr)", sm: "repeat(2, minmax(0, 1fr))" },
                gap: 2,
                mt: 2,
              }}
            >
              <UnderstandingMetric
                label="Nik Power Index"
                value={formatNpi(prediction.npi_score)}
                explanation={npiMarketNote(prediction.market)}
                metric="npi"
                market={prediction.market}
              />
              <UnderstandingMetric
                label="Confidence Rating"
                value={formatConfidence(prediction.confidence_score)}
                explanation={predictionMetricEducation.confidence.detailed}
                metric="confidence"
                market={prediction.market}
              />
              <UnderstandingMetric
                label="Projected Edge"
                value={formatProjectedEdge(prediction.projected_edge, prediction.market)}
                explanation={projectedEdgeMarketNote(prediction.market) ?? predictionMetricEducation.projectedEdge.detailed}
                metric="projectedEdge"
                market={prediction.market}
              />
              <UnderstandingMetric
                label="Model Probability"
                value={formatConfidence(prediction.simulation_probability)}
                explanation={modelProbabilityMarketNote(prediction.market) ?? predictionMetricEducation.modelProbability.detailed}
                metric="modelProbability"
                market={prediction.market}
              />
            </Box>
            {prediction.market.toLowerCase() === "total" &&
            prediction.line_value != null &&
            prediction.projected_edge != null ? (
              <Typography variant="body2" sx={{ mt: 2 }}>
                Projected total: {(prediction.line_value + prediction.projected_edge).toFixed(1)} points
              </Typography>
            ) : null}
            <Stack direction={{ xs: "column", sm: "row" }} spacing={{ xs: 0.5, sm: 2 }} sx={{ mt: 2 }}>
              <Typography variant="body2"><strong>Risk assessment:</strong> {displayRisk(prediction.risk_level)}</Typography>
              <Typography variant="body2"><strong>Model:</strong> {prediction.model_version}</Typography>
            </Stack>
          </Box>

          {prediction.reasoning ? (
            <Box>
              <Typography variant="subtitle2" fontWeight={700}>
                Model Reasoning
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