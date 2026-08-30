import InsightsOutlinedIcon from "@mui/icons-material/InsightsOutlined";
import { Box, Button, Card, CardContent, Stack, Typography } from "@mui/material";
import { Link as RouterLink } from "react-router-dom";

import type { Prediction } from "../types/product";
import {
  formatAmericanOdds,
  formatProductDate,
} from "../utils/productFormat";
import { PickMetrics } from "./PickMetrics";
import { SavePickButton } from "./SavePickButton";

interface ProductPredictionCardProps {
  prediction: Prediction;
  rank?: number;
}

function marketLabel(market: string): string {
  return market.charAt(0).toUpperCase() + market.slice(1).toLowerCase();
}

export function ProductPredictionCard({ prediction, rank }: ProductPredictionCardProps) {
  const odds = formatAmericanOdds(prediction.american_odds);

  return (
    <Card variant="outlined" sx={{ height: "100%", borderRadius: 2, backgroundColor: "background.paper", transition: "border-color 180ms ease, transform 180ms ease", "&:hover": { borderColor: "primary.main", transform: "translateY(-2px)" } }}>
      <CardContent sx={{ p: 3, "&:last-child": { pb: 3 } }}>
        <Stack spacing={3}>
          <Stack spacing={1}>
            <Typography variant="overline" color="text.secondary" sx={{ letterSpacing: 1.1 }}>
              {rank ? `#${rank}  ` : ""}{prediction.sport} · {marketLabel(prediction.market)}
            </Typography>
            <Typography variant="overline" color="text.secondary">Golden Key Best Pick</Typography>
            <Typography variant="h6">{prediction.away_team} @ {prediction.home_team}</Typography>
            <Typography variant="body2" color="text.secondary">{formatProductDate(prediction.game_date)}</Typography>
          </Stack>

          <Box>
            <Typography variant="overline" color="text.secondary">Recommended selection</Typography>
            <Typography variant="h4" sx={{ mt: 0.5 }}>{prediction.display_selection}</Typography>
            {odds ? <Typography variant="body2" color="text.secondary">Odds {odds}</Typography> : null}
            <Typography variant="caption" color="text.secondary">{prediction.model_version}</Typography>
          </Box>

          <PickMetrics
            npi={prediction.npi_score}
            confidence={prediction.confidence_score}
            simulationProbability={prediction.simulation_probability}
            projectedEdge={prediction.projected_edge}
            riskLevel={prediction.risk_level}
          />

          {prediction.reasoning ? (
            <Box sx={{ border: "1px solid", borderColor: "divider", borderRadius: 2, p: 2, backgroundColor: "action.hover" }}><Typography variant="overline" color="text.secondary">Model summary</Typography><Typography color="text.secondary" sx={{ mt: 0.5, lineHeight: 1.7, display: "-webkit-box", WebkitLineClamp: 3, WebkitBoxOrient: "vertical", overflow: "hidden" }}>{prediction.reasoning}</Typography></Box>
          ) : null}

          <Stack direction="row" spacing={1.5} flexWrap="wrap" useFlexGap>
            <SavePickButton predictionId={prediction.prediction_id} />
            <Button
              component={RouterLink}
              to={`/games/${prediction.game_id}`}
              variant="contained"
              startIcon={<InsightsOutlinedIcon />}
            >
              View Game Analysis
            </Button>
          </Stack>
        </Stack>
      </CardContent>
    </Card>
  );
}
