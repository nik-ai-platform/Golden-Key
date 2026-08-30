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
import { useNavigate } from "react-router-dom";

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

export function ProductGameCard({ predictions }: ProductGameCardProps) {
  const navigate = useNavigate();

  const sortedPredictions = [...predictions].sort(
    (a, b) => marketOrder(a.market) - marketOrder(b.market),
  );

  const game = sortedPredictions[0];

  if (!game) return null;

  return (
    <Card
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
                {game.away_team}
              </Typography>

              <Typography variant="body2" color="text.secondary" sx={{ my: 0.25 }}>
                at
              </Typography>

              <Typography variant="h5" fontWeight={700}>
                {game.home_team}
              </Typography>
            </Box>

            <Button
              variant="outlined"
              startIcon={<InsightsOutlinedIcon />}
              onClick={() => navigate(`/games/${game.game_id}`)}
              sx={{ alignSelf: { xs: "stretch", sm: "flex-start" } }}
            >
              Game analysis
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