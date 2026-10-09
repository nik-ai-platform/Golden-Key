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
import {
  formatAmericanOdds,
  formatConfidence,
  formatNpi,
  formatProductDate,
} from "../utils/productFormat";
import { SavePickButton } from "./SavePickButton";

interface ProductGameCardProps {
  predictions: Prediction[];
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
    nullableDescending(left.npi_score, right.npi_score) ||
    nullableDescending(left.confidence_score, right.confidence_score) ||
    nullableDescending(left.projected_edge, right.projected_edge)
  );
}

export function ProductGameCard({ predictions }: ProductGameCardProps) {
  const sortedPredictions = [...predictions].sort(
    (a, b) => marketOrder(a.market) - marketOrder(b.market),
  );

  const game = sortedPredictions[0];
  const bestPrediction = [...predictions]
    .filter((prediction) => prediction.recommendation_eligible !== false)
    .sort(rankPredictions)[0];

  if (!game) return null;

  return (
    <Card
      data-testid="game-card"
      data-game-id={game.game_id}
      className="gk-card"
      sx={{
        borderRadius: "var(--gk-radius-md)",
        overflow: "hidden",
        height: "100%",
        backgroundColor: "var(--gk-surface)",
        boxShadow: "var(--gk-shadow-sm)",
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
                  {formatProductDate(game.game_date)}
                </Typography>
              </Stack>

              <Typography variant="h5" fontWeight={850} sx={{ fontSize: { xs: "1.25rem", sm: "1.55rem" } }}>
                {game.away_team} @ {game.home_team}
              </Typography>
            </Box>

            <Button
              component={RouterLink}
              to={`/games/${game.game_id}`}
              variant="contained"
              startIcon={<InsightsOutlinedIcon />}
              sx={{ alignSelf: { xs: "stretch", sm: "flex-start" } }}
            >
              View Game Analysis
            </Button>
          </Stack>

          <Divider />

          <Box>
            <Typography variant="h6" fontWeight={700}>
              Bear A Hand Sports Predictions
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
                  data-testid="market-prediction-card"
                  data-best-pick={prediction.prediction_id === bestPrediction?.prediction_id}
                  sx={{
                    position: "relative",
                    backgroundColor: "var(--gk-surface-raised)",
                    borderRadius: "var(--gk-radius-sm)",
                    p: { xs: 1.75, sm: 2 },
                    height: "100%",
                    display: "flex",
                    flexDirection: "column",
                    boxShadow: "inset 0 1px 0 rgba(237, 244, 250, 0.035)",
                    ...(prediction.prediction_id === bestPrediction?.prediction_id
                      ? {
                          borderLeft: "3px solid var(--gk-lime)",
                          backgroundColor: "rgba(164, 239, 24, 0.075)",
                          boxShadow: "inset 0 0 24px rgba(164, 239, 24, 0.035)",
                        }
                      : {}),
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

                    <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                      {prediction.prediction_id === bestPrediction?.prediction_id ? (
                        <Chip
                          label="Bear A Hand Sports Best Pick"
                          size="small"
                          sx={{
                            color: "#060d14",
                            backgroundColor: "var(--gk-lime)",
                            fontWeight: 800,
                            boxShadow: "0 0 16px rgba(164, 239, 24, 0.18)",
                          }}
                        />
                      ) : null}
                      {prediction.recommendation_designation ? (
                        <Chip
                          label={prediction.recommendation_designation}
                          color="warning"
                          size="small"
                          variant="outlined"
                        />
                      ) : null}
                    </Stack>

                    <Typography variant="h6" fontWeight={800} sx={{ lineHeight: 1.35, overflowWrap: "anywhere" }}>
                      {prediction.display_selection}
                    </Typography>

                    {prediction.american_odds != null ? (
                      <Typography className="gk-data" variant="body2" sx={{ color: "var(--gk-cyan)", fontWeight: 700 }}>
                        Odds {formatAmericanOdds(prediction.american_odds)}
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

                        <Typography className="gk-data" fontWeight={700}>
                          {formatNpi(prediction.npi_score)}
                        </Typography>
                      </Box>

                      <Box>
                        <Typography variant="caption" color="text.secondary">
                          Confidence Rating
                        </Typography>

                        <Typography className="gk-data" fontWeight={700}>
                          {formatConfidence(prediction.confidence_score)}
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