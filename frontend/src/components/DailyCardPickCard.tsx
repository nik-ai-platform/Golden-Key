import InsightsOutlinedIcon from "@mui/icons-material/InsightsOutlined";
import { Box, Button, Card, CardContent, Chip, Stack, Typography } from "@mui/material";
import { Link as RouterLink } from "react-router-dom";

import type { DailyCardPick } from "../types/product";
import { formatAmericanOdds, formatProductDate } from "../utils/productFormat";
import { PickMetrics } from "./PickMetrics";
import { SavePickButton } from "./SavePickButton";

interface DailyCardPickCardProps {
  pick: DailyCardPick;
  prominent?: boolean;
}

export function DailyCardPickCard({ pick, prominent = false }: DailyCardPickCardProps) {
  const prediction = pick.prediction;
  const odds = formatAmericanOdds(prediction.american_odds);

  return (
    <Card
      variant="outlined"
      data-testid={`daily-card-${pick.role.toLowerCase().replace(/_/g, "-")}`}
      sx={{
        height: "100%",
        borderColor: prominent ? "primary.main" : "divider",
        borderRadius: 2,
        backgroundColor: "background.paper",
      }}
    >
      <CardContent
        sx={{
          p: { xs: 2.25, md: prominent ? 3.5 : 2.5 },
          "&:last-child": { pb: { xs: 2.25, md: prominent ? 3.5 : 2.5 } },
        }}
      >
        <Stack spacing={prominent ? 3 : 2.25}>
          <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" spacing={1}>
            <Box>
              <Typography variant="overline" color="primary.main" fontWeight={800}>
                {pick.label}
              </Typography>
              <Typography variant={prominent ? "h4" : "h6"} fontWeight={800} sx={{ mt: 0.25 }}>
                {prediction.display_selection}
              </Typography>
            </Box>
            <Chip
              label={`${prediction.sport} · ${prediction.market}`}
              variant="outlined"
              sx={{ alignSelf: { xs: "flex-start", sm: "center" }, textTransform: "capitalize" }}
            />
          </Stack>

          <Box>
            <Typography fontWeight={700}>
              {prediction.away_team} @ {prediction.home_team}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {formatProductDate(prediction.game_date)}
              {odds ? ` · Odds ${odds}` : ""}
            </Typography>
          </Box>

          <PickMetrics
            npi={prediction.npi_score}
            confidence={prediction.confidence_score}
            simulationProbability={prediction.simulation_probability}
            projectedEdge={prediction.projected_edge}
            riskLevel={prediction.risk_level}
          />

          <Stack
            direction="row"
            spacing={1}
            flexWrap="wrap"
            useFlexGap
            aria-label="Why this pick ranks here"
          >
            {pick.ranking_reasons.map((reason) => (
              <Chip key={reason} label={reason} size="small" variant="outlined" />
            ))}
          </Stack>

          <Stack direction="row" spacing={1.25} flexWrap="wrap" useFlexGap>
            <SavePickButton predictionId={prediction.prediction_id} />
            <Button
              component={RouterLink}
              to={`/games/${prediction.game_id}`}
              variant={prominent ? "contained" : "outlined"}
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
