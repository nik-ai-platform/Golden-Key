import InsightsOutlinedIcon from "@mui/icons-material/InsightsOutlined";
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Divider,
  Grid2 as Grid,
  Stack,
  Typography,
} from "@mui/material";
import { Link as RouterLink } from "react-router-dom";

import type { Prediction } from "../types/product";
import { SavePickButton } from "./SavePickButton";

interface ProductGameCardProps {
  predictions: Prediction[];
}

function formatGameTime(value: string): string {
  return new Date(value).toLocaleString(undefined, {
    weekday: "short",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

function formatOdds(value: number | null): string {
  if (value == null) return "";
  return value > 0 ? `+${value}` : `${value}`;
}

function marketLabel(market: string): string {
  const value = market.toLowerCase();

  if (value === "spread") return "Spread";
  if (value === "moneyline") return "Moneyline";
  if (value === "total") return "Total";

  return market;
}

function marketOrder(market: string): number {
  const value = market.toLowerCase();

  if (value === "spread") return 1;
  if (value === "moneyline") return 2;
  if (value === "total") return 3;

  return 99;
}

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

export function ProductGameCard({ predictions }: ProductGameCardProps) {
  const sortedPredictions = [...predictions].sort(
    (a, b) => marketOrder(a.market) - marketOrder(b.market),
  );

  const game = sortedPredictions[0];
  const bestPrediction = [...predictions].sort(rankPredictions)[0];

  if (!game) return null;

  return (
    <Card
      data-testid="game-card"
      data-game-id={game.game_id}
      variant="outlined"
      sx={{
        borderRadius: 3,
        overflow: "hidden",
        height: "100%",
      }}
    >
      <CardContent sx={{ p: { xs: 2, md: 3 }, "&:last-child": { pb: { xs: 2, md: 3 } } }}>
        <Stack spacing={2.5}>
          <Stack
            direction={{ xs: "column", sm: "row" }}
            justifyContent="space-between"
            spacing={1.5}
          >
            <Box>
              <Stack direction="row" spacing={1} alignItems="center" mb={1}>
                <Chip
                  label={game.sport}
                  size="small"
                  color="primary"
                  variant="outlined"
                />

                <Typography variant="body2" color="text.secondary">
                  {formatGameTime(game.game_date)}
                </Typography>
              </Stack>

              <Typography variant="h5" fontWeight={700}>
                {game.away_team} @ {game.home_team}
              </Typography>
            </Box>

            <Button
              component={RouterLink}
              to={`/games/${game.game_id}`}
              variant="outlined"
              startIcon={<InsightsOutlinedIcon />}
              sx={{ alignSelf: { xs: "stretch", sm: "flex-start" } }}
            >
              View Game Analysis
            </Button>
          </Stack>

          <Divider />

          <Box>
            <Typography variant="h6" fontWeight={700}>
              Nik AI Predictions
            </Typography>

            <Typography variant="body2" color="text.secondary">
              One prediction for each available betting market.
            </Typography>
          </Box>

          <Grid container spacing={2}>
            {sortedPredictions.map((prediction) => (
              <Grid
                key={prediction.prediction_id}
                size={{ xs: 12, md: 4 }}
              >
                <Box
                  sx={{
                    border: "1px solid",
                    borderColor: "divider",
                    borderRadius: 2,
                    p: 2,
                    height: "100%",
                    display: "flex",
                    flexDirection: "column",
                  }}
                >
                  <Stack spacing={1.5} sx={{ height: "100%" }}>
                    <Typography
                      variant="overline"
                      color="text.secondary"
                      fontWeight={700}
                    >
                      {marketLabel(prediction.market)}
                    </Typography>

                    {prediction.prediction_id === bestPrediction?.prediction_id ? (
                      <Chip
                        label="Golden Key Best Pick"
                        color="primary"
                        size="small"
                        sx={{ alignSelf: "flex-start" }}
                      />
                    ) : null}

                    <Typography variant="h6" fontWeight={700}>
                      {prediction.display_selection}
                    </Typography>

                    {prediction.american_odds != null ? (
                      <Typography variant="body2" color="text.secondary">
                        Odds {formatOdds(prediction.american_odds)}
                      </Typography>
                    ) : null}

                    <Stack
                      direction="row"
                      spacing={2}
                      flexWrap="wrap"
                      useFlexGap
                    >
                      <Box>
                        <Typography variant="caption" color="text.secondary">
                          NPI
                        </Typography>

                        <Typography fontWeight={700}>
                          {prediction.npi_score.toFixed(1)}
                        </Typography>
                      </Box>

                      <Box>
                        <Typography variant="caption" color="text.secondary">
                          Confidence
                        </Typography>

                        <Typography fontWeight={700}>
                          {prediction.confidence_score == null
                            ? "—"
                            : `${prediction.confidence_score.toFixed(1)}%`}
                        </Typography>
                      </Box>
                    </Stack>

                    <Box sx={{ flexGrow: 1 }} />

                    <SavePickButton
                      predictionId={prediction.prediction_id}
                    />
                  </Stack>
                </Box>
              </Grid>
            ))}
          </Grid>
        </Stack>
      </CardContent>
    </Card>
  );
}