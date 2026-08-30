import InsightsOutlinedIcon from "@mui/icons-material/InsightsOutlined";
import { Box, Button, Card, CardContent, Divider, Grid2 as Grid, Stack, Typography } from "@mui/material";
import { useNavigate } from "react-router-dom";

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

function formatGameTime(value: string): string {
  return new Date(value).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
}

function formatSelection(prediction: Prediction): string {
  return prediction.display_selection;
}

export function ProductPredictionCard({ prediction, rank }: ProductPredictionCardProps) {
  const navigate = useNavigate();
  const edge = prediction.projected_edge;

  return (
    <Card variant="outlined" sx={{ height: "100%", borderRadius: 2, background: "linear-gradient(180deg, rgba(255,255,255,0.96), rgba(240,253,250,0.58))", transition: "border-color 180ms ease, transform 180ms ease", "&:hover": { borderColor: "primary.main", transform: "translateY(-2px)" } }}>
      <CardContent sx={{ p: 3, "&:last-child": { pb: 3 } }}>
        <Stack spacing={3}>
          <Stack spacing={1}>
            <Typography variant="overline" color="text.secondary" sx={{ letterSpacing: 1.1 }}>
              {rank ? `#${rank}  ` : ""}{prediction.sport} · {prediction.market}
            </Typography>
            <Typography variant="h6">{prediction.away_team} at {prediction.home_team}</Typography>
            <Typography variant="body2" color="text.secondary">{formatGameTime(prediction.game_date)}</Typography>
          </Stack>

          <Box>
            <Typography variant="overline" color="text.secondary">Golden Key pick</Typography>
            <Typography variant="h4" sx={{ mt: 0.5 }}>{formatSelection(prediction)}</Typography>
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
              variant="contained"
              startIcon={<InsightsOutlinedIcon />}
              onClick={() => navigate(`/games/${prediction.game_id}`)}
            >
              View analysis
            </Button>
            <SavePickButton predictionId={prediction.prediction_id} />
          </Stack>
        </Stack>
      </CardContent>
    </Card>
  );
}
