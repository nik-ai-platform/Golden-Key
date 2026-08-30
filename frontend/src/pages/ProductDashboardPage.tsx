import ArrowForwardOutlinedIcon from "@mui/icons-material/ArrowForwardOutlined";
import {
  Box,
  Button,
  Card,
  CardContent,
  Grid2 as Grid,
  Stack,
  Typography,
} from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";

import { DashboardHero } from "../components/DashboardHero";
import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { PredictionMetric } from "../components/PredictionMetric";
import { ProductPredictionCard } from "../components/ProductPredictionCard";
import { getPerformance, getTodayPredictions } from "../services/productApi";

export function ProductDashboardPage() {
  const navigate = useNavigate();

  const predictions = useQuery({
    queryKey: ["product", "today"],
    queryFn: () => getTodayPredictions(),
  });

  const performance = useQuery({
    queryKey: ["product", "performance"],
    queryFn: getPerformance,
  });

  if (predictions.isLoading || performance.isLoading) {
    return <LoadingState message="Loading dashboard..." />;
  }

  if (predictions.isError || performance.isError) {
    return (
      <ErrorState
        kind="network"
        detail="Golden Key could not load the dashboard."
        onRetry={() => {
          void predictions.refetch();
          void performance.refetch();
        }}
      />
    );
  }

  const predictionData = predictions.data!;
  const metrics = performance.data!;

  const topPredictions = [...predictionData.predictions]
    .sort((a, b) => b.npi_score - a.npi_score)
    .slice(0, 3);

  const uniqueGames = new Map<
    number,
    {
      gameId: number;
      sport: string;
      awayTeam: string;
      homeTeam: string;
      gameDate: string;
    }
  >();

  for (const prediction of predictionData.predictions) {
    if (!uniqueGames.has(prediction.game_id)) {
      uniqueGames.set(prediction.game_id, {
        gameId: prediction.game_id,
        sport: prediction.sport,
        awayTeam: prediction.away_team,
        homeTeam: prediction.home_team,
        gameDate: prediction.game_date,
      });
    }
  }

  const upcomingGames = Array.from(uniqueGames.values())
    .sort(
      (a, b) =>
        new Date(a.gameDate).getTime() - new Date(b.gameDate).getTime(),
    )
    .slice(0, 4);

  return (
    <Stack spacing={4}>
      <DashboardHero predictionCount={predictionData.count} />

      <Box>
        <Stack
          direction={{ xs: "column", sm: "row" }}
          justifyContent="space-between"
          alignItems={{ sm: "center" }}
          spacing={1}
          sx={{ mb: 2 }}
        >
          <Box>
            <Typography variant="h5" fontWeight={700}>
              Upcoming Games
            </Typography>

            <Typography color="text.secondary" sx={{ mt: 0.5 }}>
              The next matchups currently available to Golden Key.
            </Typography>
          </Box>

          <Button
            endIcon={<ArrowForwardOutlinedIcon />}
            onClick={() => navigate("/games")}
          >
            View all games
          </Button>
        </Stack>

        {upcomingGames.length ? (
          <Grid container spacing={2}>
            {upcomingGames.map((game) => (
              <Grid
                key={game.gameId}
                size={{ xs: 12, sm: 6, xl: 3 }}
              >
                <Card
                  variant="outlined"
                  sx={{
                    height: "100%",
                    borderRadius: 2,
                    cursor: "pointer",
                    transition: "border-color 180ms ease",
                    "&:hover": {
                      borderColor: "primary.main",
                    },
                  }}
                  onClick={() => navigate(`/games/${game.gameId}`)}
                >
                  <CardContent>
                    <Stack spacing={1}>
                      <Typography
                        variant="overline"
                        color="primary.main"
                        fontWeight={700}
                      >
                        {game.sport}
                      </Typography>

                      <Typography fontWeight={700}>
                        {game.awayTeam}
                      </Typography>

                      <Typography
                        variant="body2"
                        color="text.secondary"
                      >
                        at
                      </Typography>

                      <Typography fontWeight={700}>
                        {game.homeTeam}
                      </Typography>

                      <Typography
                        variant="caption"
                        color="text.secondary"
                        sx={{ pt: 1 }}
                      >
                        {new Date(game.gameDate).toLocaleString(
                          undefined,
                          {
                            weekday: "short",
                            month: "short",
                            day: "numeric",
                            hour: "numeric",
                            minute: "2-digit",
                          },
                        )}
                      </Typography>
                    </Stack>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        ) : (
          <EmptyState
            title="No upcoming games"
            description="Upcoming matchups will appear after the odds and prediction pipeline updates."
          />
        )}
      </Box>

      <Box>
        <Stack
          direction={{ xs: "column", sm: "row" }}
          justifyContent="space-between"
          alignItems={{ sm: "center" }}
          spacing={1}
          sx={{ mb: 2 }}
        >
          <Box>
            <Typography variant="h5" fontWeight={700}>
              Top NPI Picks
            </Typography>

            <Typography color="text.secondary" sx={{ mt: 0.5 }}>
              The three strongest current predictions by Nik Power Index.
            </Typography>
          </Box>

          <Button
            endIcon={<ArrowForwardOutlinedIcon />}
            onClick={() => navigate("/games")}
          >
            View games
          </Button>
        </Stack>

        {topPredictions.length ? (
          <Grid container spacing={2.5}>
            {topPredictions.map((prediction, index) => (
              <Grid
                key={prediction.prediction_id}
                size={{ xs: 12, xl: 4 }}
              >
                <ProductPredictionCard
                  prediction={prediction}
                  rank={index + 1}
                />
              </Grid>
            ))}
          </Grid>
        ) : (
          <EmptyState
            title="No predictions available"
            description="Top NPI picks will appear when the prediction pipeline has active games."
          />
        )}
      </Box>

      <Box>
        <Stack
          direction={{ xs: "column", sm: "row" }}
          justifyContent="space-between"
          alignItems={{ sm: "center" }}
          spacing={1}
          sx={{ mb: 2 }}
        >
          <Box>
            <Typography variant="h5" fontWeight={700}>
              Performance
            </Typography>

            <Typography color="text.secondary" sx={{ mt: 0.5 }}>
              Results from settled Golden Key predictions.
            </Typography>
          </Box>

          <Button
            endIcon={<ArrowForwardOutlinedIcon />}
            onClick={() => navigate("/performance")}
          >
            Full performance
          </Button>
        </Stack>

        <Grid container spacing={2}>
          <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
            <PredictionMetric
              label="Settled picks"
              value={String(metrics.total_predictions)}
            />
          </Grid>

          <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
            <PredictionMetric
              label="Wins"
              value={String(metrics.wins)}
            />
          </Grid>

          <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
            <PredictionMetric
              label="Accuracy"
              value={`${metrics.accuracy.toFixed(1)}%`}
            />
          </Grid>

          <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
            <PredictionMetric
              label="Profit / Loss"
              value={`${metrics.profit_loss >= 0 ? "+" : ""}$${metrics.profit_loss.toFixed(2)}`}
            />
          </Grid>
        </Grid>
      </Box>
    </Stack>
  );
}
