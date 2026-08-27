import { Alert, Box, Card, CardContent, Chip, LinearProgress, Stack, Typography } from "@mui/material";

import AIExplanation from "./AIExplanation";
import ConfidenceMeter from "./ConfidenceMeter";
import NPIBadge from "./NPIBadge";
import SavePickButton from "./SavePickButton";
import SimulationCard from "./SimulationCard";
import type { Prediction } from "../types/prediction";

interface PredictionCardProps {
  prediction?: Prediction;
  matchup?: string;
  market?: string;
  pick?: string;
  confidence?: number;
  npi?: number;
  simulationProbability?: number;
  risk?: string;
  aiExplanation?: string;
}

export default function PredictionCard(props: PredictionCardProps) {
  const prediction = props.prediction;
  const matchup = props.matchup ?? `Game #${prediction?.game_id ?? "1"}`;
  const market = props.market ?? prediction?.market ?? "Spread";
  const pick = props.pick ?? prediction?.selection ?? "Home Team";
  const confidence = props.confidence ?? prediction?.confidence_score ?? 74;
  const npi = props.npi ?? prediction?.npi_score ?? 81;
  const simulationProbability = props.simulationProbability ?? prediction?.simulation_probability ?? 63;
  const risk = props.risk ?? prediction?.risk_level ?? "Medium";
  const aiExplanation = props.aiExplanation ?? prediction?.reasoning ?? "AI analysis indicates favorable market movement and stable matchup indicators.";

  return (
    <Card elevation={3} sx={{ borderRadius: 3 }}>
      <CardContent>
        <Stack spacing={2.5}>
          <Stack direction="row" justifyContent="space-between" alignItems="center" spacing={2}>
            <div>
              <Typography variant="overline" color="text.secondary">
                {market}
              </Typography>
              <Typography variant="h5">{matchup}</Typography>
            </div>
            <Chip label={risk} color={risk === "High" ? "error" : risk === "Low" ? "success" : "warning"} />
          </Stack>

          <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
            <Stack spacing={0.5} flex={1}>
              <Typography variant="caption" color="text.secondary">
                Pick
              </Typography>
              <Typography variant="h6">{pick}</Typography>
            </Stack>
            <Stack spacing={0.5} flex={1}>
              <Typography variant="caption" color="text.secondary">
                Confidence
              </Typography>
              <Typography variant="h6">{confidence}%</Typography>
            </Stack>
            <Stack spacing={0.5} flex={1}>
              <Typography variant="caption" color="text.secondary">
                NPI
              </Typography>
              <Typography variant="h6">{npi}</Typography>
            </Stack>
            <Stack spacing={0.5} flex={1}>
              <Typography variant="caption" color="text.secondary">
                Simulation
              </Typography>
              <Typography variant="h6">{simulationProbability}%</Typography>
            </Stack>
          </Stack>

          <Box>
            <LinearProgress variant="determinate" value={Math.max(0, Math.min(100, confidence))} sx={{ height: 8, borderRadius: 999 }} />
          </Box>

          <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
            <Box sx={{ flex: 1 }}>
              <NPIBadge score={npi} />
            </Box>
            <Box sx={{ flex: 1 }}>
              <ConfidenceMeter confidence={confidence} />
            </Box>
          </Stack>

          <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
            <Box sx={{ flex: 1 }}>
              <SimulationCard probability={simulationProbability} margin={prediction?.simulation_margin ?? 0} runs={prediction?.simulation_runs ?? 0} />
            </Box>
            <Box sx={{ flex: 1 }}>
              <AIExplanation explanation={aiExplanation} />
            </Box>
          </Stack>

          <Alert severity="info" sx={{ alignItems: "center" }}>
            {aiExplanation}
          </Alert>

          {prediction?.id ? <SavePickButton predictionId={prediction.id} /> : null}
        </Stack>
      </CardContent>
    </Card>
  );
}
