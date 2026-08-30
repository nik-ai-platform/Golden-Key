import InsightsOutlinedIcon from "@mui/icons-material/InsightsOutlined";
import { Box, Button, Card, CardContent, Divider, Grid2 as Grid, Stack, Typography } from "@mui/material";
import { Link as RouterLink } from "react-router-dom";

import type { Prediction } from "../types/product";
import { NPIScore } from "./NPIScore";
import { PredictionMetric } from "./PredictionMetric";
import { SavePickButton } from "./SavePickButton";

interface ProductPredictionCardProps {
  prediction: Prediction;
  rank?: number;
}

function percentage(value: number | null): string {
  return value == null ? "Not rated" : `${value.toFixed(1)}%`;
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

function marketLabel(market: string): string {
  return market.charAt(0).toUpperCase() + market.slice(1).toLowerCase();
}

function americanOdds(value: number | null): string | null {
  if (value == null) return null;
  return value > 0 ? `+${value}` : String(value);
}

export function ProductPredictionCard({ prediction, rank }: ProductPredictionCardProps) {
  const edge = prediction.projected_edge;
  const odds = americanOdds(prediction.american_odds);

  return (
    <Card variant="outlined" sx={{ height: "100%", borderRadius: 2, background: "linear-gradient(180deg, rgba(255,255,255,0.96), rgba(240,253,250,0.58))", transition: "border-color 180ms ease, transform 180ms ease", "&:hover": { borderColor: "primary.main", transform: "translateY(-2px)" } }}>
      <CardContent sx={{ p: 3, "&:last-child": { pb: 3 } }}>
        <Stack spacing={3}>
          <Stack spacing={1}>
            <Typography variant="overline" color="text.secondary" sx={{ letterSpacing: 1.1 }}>
              {rank ? `#${rank}  ` : ""}{prediction.sport} · {marketLabel(prediction.market)}
            </Typography>
            <Typography variant="h6">{prediction.away_team} @ {prediction.home_team}</Typography>
            <Typography variant="body2" color="text.secondary">{formatGameDate(prediction.game_date)}</Typography>
          </Stack>

          <Box>
            <Typography variant="overline" color="text.secondary">Golden Key pick</Typography>
            <Typography variant="h4" sx={{ mt: 0.5 }}>{prediction.display_selection}</Typography>
            {odds ? <Typography variant="body2" color="text.secondary">Odds {odds}</Typography> : null}
            <Typography variant="caption" color="text.secondary">{prediction.model_version}</Typography>
          </Box>

          <Divider />
          <NPIScore score={prediction.npi_score} />

          <Grid container spacing={1.5}>
            <Grid size={{ xs: 6, md: 3 }}><PredictionMetric label="Confidence" value={percentage(prediction.confidence_score)} /></Grid>
            <Grid size={{ xs: 6, md: 3 }}><PredictionMetric label="Simulation" value={percentage(prediction.simulation_probability)} /></Grid>
            <Grid size={{ xs: 6, md: 3 }}>
              <PredictionMetric label="Projected edge" value={edge == null ? "Not rated" : `${edge >= 0 ? "+" : ""}${edge.toFixed(1)}%`} />
            </Grid>
            <Grid size={{ xs: 6, md: 3 }}><PredictionMetric label="Risk" value={(prediction.risk_level ?? "Unrated").toUpperCase()} /></Grid>
          </Grid>

          {prediction.reasoning ? (
            <Box sx={{ border: "1px solid", borderColor: "divider", borderRadius: 2, p: 2, backgroundColor: "rgba(255,255,255,0.55)" }}><Typography variant="overline" color="text.secondary">Model summary</Typography><Typography color="text.secondary" sx={{ mt: 0.5, lineHeight: 1.7, display: "-webkit-box", WebkitLineClamp: 3, WebkitBoxOrient: "vertical", overflow: "hidden" }}>{prediction.reasoning}</Typography></Box>
          ) : null}

          <Stack direction="row" spacing={1.5} flexWrap="wrap" useFlexGap>
            <Button
              component={RouterLink}
              to={`/games/${prediction.game_id}`}
              variant="contained"
              startIcon={<InsightsOutlinedIcon />}
            >
              View game analysis
            </Button>
            <SavePickButton predictionId={prediction.prediction_id} />
          </Stack>
        </Stack>
      </CardContent>
    </Card>
  );
}
