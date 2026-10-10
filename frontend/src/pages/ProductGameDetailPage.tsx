import ArrowBackOutlinedIcon from "@mui/icons-material/ArrowBackOutlined";
import ExpandMoreOutlinedIcon from "@mui/icons-material/ExpandMoreOutlined";
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
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
  customerFacingReasoning,
} from "../utils/productFormat";

const MARKET_ORDER = ["spread", "moneyline", "total"];

function nullableDescending(left: number | null, right: number | null): number {
  return (right ?? Number.NEGATIVE_INFINITY) -
    (left ?? Number.NEGATIVE_INFINITY);
}

function rankPredictions(left: Prediction, right: Prediction): number {
  return (
    nullableDescending(left.npi_score, right.npi_score) ||
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

function isNoSelection(selection: string): boolean {
  return ["PASS", "NO_BET", "NOBET"].includes(selection.trim().toUpperCase());
}

function splitEvidence(value: string | undefined): string[] {
  return value
    ? value.split(/\s*,\s*/).map((part) => part.trim()).filter(Boolean)
    : [];
}

function recordedEvidence(reasoning: string | null): {
  supporting: string[];
  uncertainties: string[];
} {
  if (!reasoning) return { supporting: [], uncertainties: [] };

  const text = customerFacingReasoning(reasoning) ?? "";
  const advantages = text.match(/Key Advantages:\s*(.*?)(?=\s+Risk Factors:|$)/i)?.[1];
  const risks = text.match(/Risk Factors:\s*(.*?)(?=$)/i)?.[1];
  let remainder = text
    .replace(/Key Advantages:\s*.*?(?=\s+Risk Factors:|$)/i, " ")
    .replace(/Risk Factors:\s*.*$/i, " ")
    .replace(/^(?:Spread|Moneyline|Total) model\.\s*/i, "")
    .replace(/NPI Score:\s*[^.]+\.\s*/i, "")
    .replace(/Model Probability:\s*[^.]+\.\s*/i, "")
    .replace(/\s+/g, " ")
    .trim();

  const supporting = splitEvidence(advantages);
  if (supporting.length === 0 && remainder) {
    supporting.push(remainder);
  }
  if (supporting.length > 0) remainder = "";

  return {
    supporting: supporting.slice(0, 3),
    uncertainties: splitEvidence(risks).slice(0, 3),
  };
}

function formatRecordedValue(value: number | null | undefined): string {
  if (value == null || !Number.isFinite(value)) return "Not recorded";
  return String(value);
}

function formatRecordedTime(value: string | null | undefined): string | null {
  if (!value) return null;
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed.toLocaleString();
}

function SignalBreakdown({ prediction }: { prediction: Prediction }) {
  const breakdown = prediction.signal_breakdown;
  const noSelection = isNoSelection(prediction.selection);
  const odds = breakdown?.frozen_odds;
  const predictionTime = formatRecordedTime(breakdown?.prediction_recorded_at);
  const oddsTime = formatRecordedTime(odds?.recorded_at);

  return (
    <Accordion
      disableGutters
      elevation={0}
      sx={{
        backgroundColor: "var(--gk-surface-soft)",
        borderRadius: "12px !important",
        "&::before": { display: "none" },
        "&.Mui-expanded": { my: 0 },
      }}
    >
      <AccordionSummary
        expandIcon={<ExpandMoreOutlinedIcon />}
        aria-controls={`signal-breakdown-${prediction.prediction_id}-content`}
        id={`signal-breakdown-${prediction.prediction_id}-header`}
        sx={{
          px: { xs: 1.5, sm: 2 },
          "& .MuiAccordionSummary-content": { my: 1.25 },
          "&:focus-visible": { outline: "2px solid var(--gk-cyan)", outlineOffset: -2 },
        }}
      >
        <Typography fontWeight={800}>View signal breakdown</Typography>
      </AccordionSummary>
      <AccordionDetails
        id={`signal-breakdown-${prediction.prediction_id}-content`}
        sx={{ px: { xs: 1.5, sm: 2 }, pt: 0, pb: 2 }}
      >
        {!breakdown || breakdown.factors.length === 0 ? (
          <Typography color="text.secondary">
            Detailed breakdown unavailable for this pick.
          </Typography>
        ) : (
          <Stack spacing={2}>
            <Box>
              <Typography variant="subtitle2" fontWeight={800}>
                Recorded model factors · {breakdown.model_version}
              </Typography>
              {predictionTime ? (
                <Typography variant="caption" color="text.secondary">
                  Prediction recorded {predictionTime}
                </Typography>
              ) : null}
            </Box>
            {noSelection ? (
              <Typography color="text.secondary">
                This {prediction.selection} record has no recommended side. The entries below are recorded market/model signals, not a pick.
              </Typography>
            ) : null}
            <Stack spacing={1}>
              {breakdown.factors.map((factor, index) => {
                const factorTime = formatRecordedTime(factor.recorded_at);
                return (
                  <Box
                    key={`${factor.factor_name}-${index}`}
                    sx={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "flex-start",
                      gap: 2,
                      py: 0.75,
                      borderBottom: "1px solid rgba(169, 188, 203, 0.12)",
                    }}
                  >
                    <Box sx={{ minWidth: 0 }}>
                      <Typography fontWeight={700}>{factor.factor_name}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        Recorded side: {factor.predicted_side || "Unavailable"}
                        {factorTime ? ` · ${factorTime}` : ""}
                      </Typography>
                    </Box>
                    <Typography
                      className="gk-data"
                      sx={{ color: "var(--gk-cyan)", flexShrink: 0, textAlign: "right" }}
                    >
                      {formatRecordedValue(factor.factor_score)} / {formatRecordedValue(factor.weight)}
                    </Typography>
                  </Box>
                );
              })}
            </Stack>
            {breakdown.recorded_explanation ? (
              <Box>
                <Typography variant="subtitle2" fontWeight={750}>Stored explanation trace</Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5, lineHeight: 1.65 }}>
                  {customerFacingReasoning(breakdown.recorded_explanation)}
                </Typography>
              </Box>
            ) : null}
            {odds ? (
              <Box>
                <Typography variant="subtitle2" fontWeight={750}>Frozen sportsbook inputs</Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                  Spread home/away: {formatRecordedValue(odds.spread_home)} / {formatRecordedValue(odds.spread_away)}
                  {" · "}Moneyline home/away: {formatRecordedValue(odds.moneyline_home)} / {formatRecordedValue(odds.moneyline_away)}
                  {" · "}Total: {formatRecordedValue(odds.total)}
                </Typography>
                {oddsTime ? (
                  <Typography variant="caption" color="text.secondary">
                    Snapshot {odds.snapshot_id}{odds.sportsbook ? ` · ${odds.sportsbook}` : ""} · recorded {oddsTime}
                  </Typography>
                ) : (
                  <Typography variant="caption" color="text.secondary">
                    Snapshot {odds.snapshot_id}{odds.sportsbook ? ` · ${odds.sportsbook}` : ""}
                  </Typography>
                )}
              </Box>
            ) : (
              <Typography variant="caption" color="text.secondary">
                A frozen sportsbook input snapshot is not linked to this prediction.
              </Typography>
            )}
          </Stack>
        )}
      </AccordionDetails>
    </Accordion>
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
  const noSelection = isNoSelection(prediction.selection);
  const evidence = noSelection
    ? { supporting: [], uncertainties: [] }
    : recordedEvidence(prediction.reasoning);
  const matchup = `${prediction.away_team} @ ${prediction.home_team}`;
  const oddsObservedAt = formatRecordedTime(prediction.odds_observed_at);

  return (
    <Card
      data-testid="market-prediction-card"
      sx={{
        height: "100%",
        borderRadius: "16px",
        backgroundColor: "var(--gk-surface)",
        boxShadow: "0 16px 40px rgba(0, 0, 0, 0.26), 0 0 22px rgba(0, 212, 255, 0.055)",
      }}
    >
      <CardContent sx={{ p: { xs: 2, md: 2.75 }, "&:last-child": { pb: { xs: 2, md: 2.75 } } }}>
        <Stack spacing={2}>
          <Stack direction="row" justifyContent="space-between" alignItems="center" spacing={1}>
            <Typography variant="overline" color="text.secondary" fontWeight={700}>
              {marketLabel(prediction.market)}
            </Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap justifyContent="flex-end">
              {isBestPick ? <Chip label="Bear A Hand Sports Best Pick" color="primary" size="small" /> : null}
              {prediction.recommendation_designation ? (
                <Chip
                  label={prediction.recommendation_designation}
                  color="warning"
                  size="small"
                  variant="outlined"
                />
              ) : null}
              {(prediction.result_status ?? prediction.outcome) ? (
                <Chip
                  label={
                    (prediction.result_status ?? prediction.outcome)?.toUpperCase() === "NO_BET"
                      ? "NO BET"
                      : prediction.result_status ?? prediction.outcome
                  }
                  color={outcomeColor(
                    (prediction.result_status ?? prediction.outcome)?.toUpperCase() ?? "",
                  )}
                  size="small"
                />
              ) : null}
            </Stack>
          </Stack>

          <Box
            component="section"
            aria-label={`Understanding this ${prediction.market} pick`}
            sx={{
              borderTop: "1px solid rgba(0, 212, 255, 0.16)",
              pt: 2,
            }}
          >
            <Typography variant="h6" fontWeight={800}>
              Understanding This Pick
            </Typography>
            <Typography variant="overline" color="secondary.main" fontWeight={800}>
              Pick Brief
            </Typography>
            <Typography variant="body1" fontWeight={750} sx={{ mt: 0.5 }}>
              {matchup}
            </Typography>
            <Stack direction="row" spacing={1} alignItems="center" useFlexGap flexWrap="wrap" sx={{ mt: 0.75 }}>
              <Chip label={marketLabel(prediction.market)} size="small" color="secondary" />
              <Typography
                variant="h6"
                fontWeight={850}
                sx={{ color: noSelection ? "text.secondary" : "var(--gk-lime)", overflowWrap: "anywhere" }}
              >
                {noSelection ? `No selection recorded (${prediction.selection})` : prediction.display_selection}
              </Typography>
            </Stack>
            {prediction.market.toLowerCase() !== "moneyline" && prediction.line_value != null ? (
              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                {prediction.market.toLowerCase() === "total" ? "Game total" : "Selected-side line"}: {formatScore(prediction.line_value)}
              </Typography>
            ) : null}
            {prediction.american_odds != null ? (
              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                Quoted odds {formatAmericanOdds(prediction.american_odds)}
                {prediction.sportsbook ? ` · ${prediction.sportsbook}` : ""}
                {oddsObservedAt ? ` · observed ${oddsObservedAt}` : ""}
              </Typography>
            ) : (
              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                Quoted odds were not recorded.
              </Typography>
            )}

            <Box sx={{ mt: 2 }}>
              <Typography variant="subtitle2" fontWeight={800}>Recorded support</Typography>
              {evidence.supporting.length ? (
                <Stack component="ul" spacing={0.5} sx={{ mt: 0.75, mb: 0, pl: 2.5 }}>
                  {evidence.supporting.map((reason, index) => (
                    <Typography component="li" variant="body2" color="text.secondary" key={`${reason}-${index}`}>
                      {reason}
                    </Typography>
                  ))}
                </Stack>
              ) : (
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                  No pick-specific supporting reasons were recorded.
                </Typography>
              )}
            </Box>
            <Box sx={{ mt: 1.5 }}>
              <Typography variant="subtitle2" fontWeight={800}>Main uncertainty</Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                {evidence.uncertainties[0] ?? "No pick-specific uncertainty was recorded."}
              </Typography>
            </Box>

            <Box sx={{ mt: 2 }}>
              <PickMetrics
                npi={prediction.npi_score}
                confidence={prediction.confidence_score}
                simulationProbability={prediction.simulation_probability}
                projectedEdge={prediction.projected_edge}
                riskLevel={prediction.risk_level}
                market={prediction.market}
              />
            </Box>

            <Box sx={{ mt: 1.5 }}>
              <SignalBreakdown prediction={prediction} />
            </Box>
          </Box>

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
  const bestPrediction = [...predictions]
    .filter((prediction) => prediction.recommendation_eligible !== false)
    .sort(rankPredictions)[0];
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
        <EmptyState title="No Bear A Hand Sports predictions are available for this game yet." />
      ) : (
        <Box component="section" aria-label="Bear A Hand Sports recommendations">
          <Typography variant="h5" fontWeight={700} sx={{ mb: 2 }}>
            Bear A Hand Recommendations
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