import { useMutation, useQuery } from "@tanstack/react-query";
import { Box, Button, Card, CardContent, Grid2 as Grid, LinearProgress, MenuItem, Stack, TextField, Typography } from "@mui/material";
import { useMemo, useState } from "react";

import { getPersonalizedRecommendations, getUserProfile, updateUserProfile } from "../services/personalizationService";
import { getUserPreferences, updateUserPreferences } from "../services/preferencesService";
import { createStrategy, listStrategies, simulateStrategy } from "../services/strategyService";
import { askCoach, getCoachBriefing } from "../services/coachService";

import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { getCalibration, getConfidence } from "../services/analyticsService";
import { getDashboard } from "../services/dashboardService";
import { getSportComparison, getSportFeatures, getSports } from "../services/sportsService";
import { getLiveAlerts, getLiveGame, getLiveProbability, getLiveSignals, getLiveStream } from "../services/liveService";
import { explainModel, getModelPerformance, getModelStatus } from "../services/modelService";
import { getChampionModel, getModelDrift, getTrainingJobs } from "../services/modelOperationsService";
import { classifyError } from "../utils/apiError";
import { formatNumber, formatPercent } from "../utils/format";

export function DashboardPage() {
  const dashboardQuery = useQuery({ queryKey: ["dashboard"], queryFn: getDashboard });
  const confidenceQuery = useQuery({ queryKey: ["confidence"], queryFn: getConfidence });
  const calibrationQuery = useQuery({ queryKey: ["calibration"], queryFn: getCalibration });
  const profileQuery = useQuery({ queryKey: ["user-profile"], queryFn: getUserProfile });
  const recommendationsQuery = useQuery({ queryKey: ["personalized-recommendations"], queryFn: getPersonalizedRecommendations });
  const preferencesQuery = useQuery({ queryKey: ["user-preferences"], queryFn: getUserPreferences });
  const strategiesQuery = useQuery({ queryKey: ["strategies"], queryFn: listStrategies });
  const sportsQuery = useQuery({ queryKey: ["sports"], queryFn: getSports });
  const comparisonQuery = useQuery({ queryKey: ["sports-comparison"], queryFn: getSportComparison });
  const nbaFeaturesQuery = useQuery({ queryKey: ["sports-nba-features"], queryFn: () => getSportFeatures("NBA") });
  const liveGameQuery = useQuery({ queryKey: ["live-game"], queryFn: () => getLiveGame(42) });
  const liveProbabilityQuery = useQuery({ queryKey: ["live-probability"], queryFn: () => getLiveProbability(42) });
  const liveSignalsQuery = useQuery({ queryKey: ["live-signals"], queryFn: getLiveSignals });
  const liveAlertsQuery = useQuery({ queryKey: ["live-alerts"], queryFn: getLiveAlerts });
  const liveStreamQuery = useQuery({ queryKey: ["live-stream"], queryFn: getLiveStream });
  const modelStatusQuery = useQuery({ queryKey: ["model-status"], queryFn: getModelStatus });
  const modelPerformanceQuery = useQuery({ queryKey: ["model-performance"], queryFn: getModelPerformance });
  const explanationQuery = useQuery({ queryKey: ["model-explanation"], queryFn: () => explainModel(42) });
  const championQuery = useQuery({ queryKey: ["champion-model"], queryFn: getChampionModel });
  const driftQuery = useQuery({ queryKey: ["model-drift"], queryFn: getModelDrift });
  const jobsQuery = useQuery({ queryKey: ["training-jobs"], queryFn: getTrainingJobs });
  const [riskLevel, setRiskLevel] = useState("MODERATE");
  const [sports, setSports] = useState("NFL, NBA");
  const [markets, setMarkets] = useState("ATS, Moneyline");
  const [minimumConfidence, setMinimumConfidence] = useState("75");
  const [minimumEdge, setMinimumEdge] = useState("3");
  const [maxParlayLegs, setMaxParlayLegs] = useState("3");
  const [avoidHighVariance, setAvoidHighVariance] = useState(true);
  const [strategyName, setStrategyName] = useState("NBA Value Hunter");
  const [simulationResult, setSimulationResult] = useState<string | Record<string, unknown> | null>(null);
  const [coachQuestion, setCoachQuestion] = useState("Should I bet this?");
  const [coachAnswer, setCoachAnswer] = useState<string | null>(null);
  const [coachWarnings, setCoachWarnings] = useState<string[]>([]);

  const momentumValue = Math.min(100, Math.max(0, (liveGameQuery.data?.momentum_score ?? 0) * 10));
  const scoreDifferential = (liveGameQuery.data?.home_score ?? 0) - (liveGameQuery.data?.away_score ?? 0);
  const recentEvents = [
    { title: "Momentum", detail: `${liveGameQuery.data?.momentum_score ?? 0} swing points` },
    { title: "Possession", detail: `${liveGameQuery.data?.possession ?? "HOME"} controls the pace` },
    { title: "Signal", detail: liveSignalsQuery.data?.signal ?? "VALUE" },
  ];

  const mutation = useMutation({
    mutationFn: updateUserProfile,
    onSuccess: async () => {
      await profileQuery.refetch();
      await recommendationsQuery.refetch();
    },
  });

  const preferencesMutation = useMutation({
    mutationFn: updateUserPreferences,
    onSuccess: async () => {
      await preferencesQuery.refetch();
    },
  });

  const coachBriefingQuery = useQuery({ queryKey: ["coach-briefing"], queryFn: () => getCoachBriefing(profileQuery.data?.user_id ?? 1) });

  useMemo(() => {
    if (profileQuery.data) {
      setRiskLevel(profileQuery.data.risk_level ?? "MODERATE");
      setSports((profileQuery.data.preferred_sports ?? ["NFL", "NBA"]).join(", "));
      setMarkets((profileQuery.data.preferred_markets ?? ["ATS", "Moneyline"]).join(", "));
    }
    if (preferencesQuery.data) {
      setMinimumConfidence(String(preferencesQuery.data.minimum_confidence ?? 75));
      setMinimumEdge(String(preferencesQuery.data.minimum_edge ?? 3));
      setMaxParlayLegs(String(preferencesQuery.data.max_parlay_legs ?? 3));
      setAvoidHighVariance(Boolean(preferencesQuery.data.avoid_high_variance ?? true));
    }
  }, [profileQuery.data, preferencesQuery.data]);

  if (dashboardQuery.isLoading || confidenceQuery.isLoading || calibrationQuery.isLoading || profileQuery.isLoading || recommendationsQuery.isLoading || preferencesQuery.isLoading) {
    return <LoadingState message="Loading dashboard..." />;
  }

  if (dashboardQuery.isError || confidenceQuery.isError || calibrationQuery.isError || profileQuery.isError || recommendationsQuery.isError || preferencesQuery.isError || !dashboardQuery.data || !confidenceQuery.data || !calibrationQuery.data || !profileQuery.data) {
    return (
      <ErrorState
        {...classifyError(dashboardQuery.error ?? confidenceQuery.error ?? calibrationQuery.error ?? profileQuery.error ?? recommendationsQuery.error ?? preferencesQuery.error)}
        onRetry={() => {
          void dashboardQuery.refetch();
          void confidenceQuery.refetch();
          void calibrationQuery.refetch();
          void profileQuery.refetch();
          void recommendationsQuery.refetch();
          void preferencesQuery.refetch();
        }}
      />
    );
  }

  async function handleCoachAsk() {
    const response = await askCoach({ user_id: profileQuery.data?.user_id ?? 1, question: coachQuestion });
    setCoachAnswer(response.answer ?? null);
    setCoachWarnings(response.warnings ?? []);
  }

  async function handleSave() {
    mutation.mutate({
      user_id: profileQuery.data?.user_id ?? 1,
      risk_level: riskLevel,
      preferred_sports: sports.split(",").map((item) => item.trim()).filter(Boolean),
      preferred_markets: markets.split(",").map((item) => item.trim()).filter(Boolean),
      betting_style: "balanced",
    });

    preferencesMutation.mutate({
      minimum_confidence: Number(minimumConfidence),
      minimum_edge: Number(minimumEdge),
      max_parlay_legs: Number(maxParlayLegs),
      avoid_high_variance: avoidHighVariance,
      preferred_odds_range: "-110 to +150",
    });

    await createStrategy({
      user_id: profileQuery.data?.user_id ?? 1,
      strategy_name: strategyName,
      sport: sports.split(",")[0]?.trim() || "NBA",
      market_type: markets.split(",")[0]?.trim() || "ATS",
      rules: {
        confidence_threshold: Number(minimumConfidence),
        minimum_edge: Number(minimumEdge),
        parlay_rules: avoidHighVariance ? "single" : "allow_parlays",
      },
      starting_bankroll: 5000,
    });

    const result = await simulateStrategy({
      strategy: { strategy_name: strategyName, sport: sports.split(",")[0]?.trim() || "NBA", market: markets.split(",")[0]?.trim() || "ATS" },
      historical_games: [{ outcome: "win" }, { outcome: "loss" }],
    });
    setSimulationResult(result as string | Record<string, unknown> | null);
  }

  return (
    <Stack spacing={2.5}>
      <Typography variant="h4">Dashboard</Typography>
      <Grid container spacing={2}>
        <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
          <MetricCard title="Overall Accuracy" value={formatPercent(dashboardQuery.data.overall_accuracy)} />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
          <MetricCard title="Total Predictions" value={formatNumber(dashboardQuery.data.total_predictions)} />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
          <MetricCard title="Avg Confidence" value={formatPercent(confidenceQuery.data.average_confidence)} />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
          <MetricCard title="System Health" value={dashboardQuery.data.system_health.toUpperCase()} />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, lg: 3 }}>
          <MetricCard title="Calibration Reliability" value={formatPercent(calibrationQuery.data.overall_reliability)} />
        </Grid>
      </Grid>

      <Card sx={{ background: "linear-gradient(140deg, #ecfeff 0%, #f8fafc 70%)" }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>Personal Betting Center</Typography>
          <Typography color="text.secondary" sx={{ mb: 2 }}>
            Your profile, preferred sports, and personalized recommendations.
          </Typography>
          <Grid container spacing={2}>
            <Grid size={{ xs: 12, md: 6 }}>
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="subtitle1" fontWeight={700}>Your Profile</Typography>
                  <Stack spacing={1.5} mt={1}>
                    <TextField
                      select
                      label="Risk Level"
                      value={riskLevel}
                      onChange={(event) => setRiskLevel(event.target.value)}
                    >
                      <MenuItem value="CONSERVATIVE">Conservative</MenuItem>
                      <MenuItem value="MODERATE">Moderate</MenuItem>
                      <MenuItem value="AGGRESSIVE">Aggressive</MenuItem>
                      <MenuItem value="PROFESSIONAL">Professional</MenuItem>
                    </TextField>
                    <TextField label="Preferred Sports" value={sports} onChange={(event) => setSports(event.target.value)} />
                    <TextField label="Preferred Markets" value={markets} onChange={(event) => setMarkets(event.target.value)} />
                    <TextField label="Minimum Confidence" type="number" value={minimumConfidence} onChange={(event) => setMinimumConfidence(event.target.value)} />
                    <TextField label="Minimum Edge" type="number" value={minimumEdge} onChange={(event) => setMinimumEdge(event.target.value)} />
                    <TextField label="Max Parlay Legs" type="number" value={maxParlayLegs} onChange={(event) => setMaxParlayLegs(event.target.value)} />
                    <TextField
                      select
                      label="Avoid High Variance"
                      value={avoidHighVariance ? "yes" : "no"}
                      onChange={(event) => setAvoidHighVariance(event.target.value === "yes")}
                    >
                      <MenuItem value="yes">Yes</MenuItem>
                      <MenuItem value="no">No</MenuItem>
                    </TextField>
                    <Button variant="contained" onClick={handleSave} disabled={mutation.isPending || preferencesMutation.isPending}>
                      {mutation.isPending || preferencesMutation.isPending ? "Saving..." : "Save Profile"}
                    </Button>
                  </Stack>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, md: 6 }}>
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="subtitle1" fontWeight={700}>Recommended Today</Typography>
                  <Typography variant="h5">{recommendationsQuery.data?.length ?? 1} Games</Typography>
                  <Typography variant="body2" color="text.secondary">Personalized picks tuned to your risk profile.</Typography>
                </CardContent>
              </Card>
              <Card variant="outlined" sx={{ mt: 1.5 }}>
                <CardContent>
                  <Typography variant="subtitle1" fontWeight={700}>Strategy Lab</Typography>
                  <TextField label="Strategy Name" fullWidth value={strategyName} onChange={(event) => setStrategyName(event.target.value)} sx={{ mt: 1 }} />
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                    {strategiesQuery.data?.[0]?.strategy_name ?? "NBA Conservative ATS"}
                  </Typography>
                  {simulationResult && (
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                      Simulation: {typeof simulationResult === "string" ? simulationResult : JSON.stringify(simulationResult)}
                    </Typography>
                  )}
                </CardContent>
              </Card>
              <Card variant="outlined" sx={{ mt: 1.5 }}>
                <CardContent>
                  <Typography variant="subtitle1" fontWeight={700}>Golden Key Coach</Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                    {coachBriefingQuery.data?.briefing?.headline ?? "Good Morning"}
                  </Typography>
                  <TextField label="Ask anything" fullWidth value={coachQuestion} onChange={(event) => setCoachQuestion(event.target.value)} sx={{ mt: 1.5 }} />
                  <Button variant="outlined" onClick={() => { void handleCoachAsk(); }} sx={{ mt: 1.5 }}>
                    Ask Coach
                  </Button>
                  {coachAnswer && (
                    <Typography variant="body2" color="text.secondary" sx={{ mt: 1.5 }}>
                      {coachAnswer}
                    </Typography>
                  )}
                  {coachWarnings.length > 0 && (
                    <Stack spacing={0.5} sx={{ mt: 1.5 }}>
                      {coachWarnings.map((warning) => (
                        <Typography key={warning} variant="body2" color="warning.main">{warning}</Typography>
                      ))}
                    </Stack>
                  )}
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>Sports Intelligence Center</Typography>
          <Typography color="text.secondary" sx={{ mb: 2 }}>
            Multi-sport model health, feature coverage, and league comparison insights.
          </Typography>
          <Grid container spacing={2}>
            {sportsQuery.data?.map((sport) => (
              <Grid size={{ xs: 12, sm: 6, md: 3 }} key={sport.sport}>
                <Card variant="outlined">
                  <CardContent>
                    <Typography variant="subtitle1" fontWeight={700}>{sport.sport}</Typography>
                    <Typography variant="body2" color="text.secondary">Model: {sport.model}</Typography>
                    <Typography variant="body2" color="text.secondary">Health: {sport.health}</Typography>
                  </CardContent>
                </Card>
              </Grid>
            ))}
            <Grid size={{ xs: 12, md: 6 }}>
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="subtitle1" fontWeight={700}>NBA Features</Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                    {nbaFeaturesQuery.data?.features?.join(", ") ?? "pace, efficiency, rest"}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, md: 6 }}>
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="subtitle1" fontWeight={700}>League Comparison</Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                    {comparisonQuery.data ? JSON.stringify(comparisonQuery.data) : "Loading comparison data..."}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>Live Intelligence Center</Typography>
          <Typography color="text.secondary" sx={{ mb: 2 }}>
            Real-time state, probabilities, signals, alerts, and streaming status for the active game.
          </Typography>
          <Grid container spacing={2}>
            <Grid size={{ xs: 12, md: 4 }}>
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="subtitle1" fontWeight={700}>Live Game Snapshot</Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                    Game ID: {liveGameQuery.data?.game_id ?? 42}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Score: {liveGameQuery.data?.home_score ?? 0} - {liveGameQuery.data?.away_score ?? 0}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Differential: {scoreDifferential > 0 ? `+${scoreDifferential}` : scoreDifferential}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Quarter: {liveGameQuery.data?.quarter_period ?? "Q1"} · Clock: {liveGameQuery.data?.clock ?? "00:00"}
                  </Typography>
                  <Box sx={{ mt: 1.5 }}>
                    <Typography variant="caption" color="text.secondary">Momentum</Typography>
                    <LinearProgress variant="determinate" value={momentumValue} sx={{ height: 8, borderRadius: 999, mt: 0.5 }} />
                  </Box>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, md: 4 }}>
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="subtitle1" fontWeight={700}>Live Probabilities</Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                    Win: {liveProbabilityQuery.data?.win_probability ?? 68}%
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Cover: {liveProbabilityQuery.data?.cover_probability ?? 62}%
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Total: {liveProbabilityQuery.data?.total_probability ?? 58}%
                  </Typography>
                  <Typography variant="body2" color="primary.main" sx={{ mt: 1.25 }}>
                    Edge is building as the game unfolds.
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, md: 4 }}>
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="subtitle1" fontWeight={700}>Signals & Alerts</Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                    Signal: {liveSignalsQuery.data?.signal ?? "VALUE"}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Alert: {liveAlertsQuery.data?.alert ?? "Probability Shift"}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Stream: {liveStreamQuery.data?.status ?? "streaming"}
                  </Typography>
                  <Stack spacing={0.75} sx={{ mt: 1.25 }}>
                    {recentEvents.map((event) => (
                      <Typography key={event.title} variant="body2" color="text.secondary">
                        • {event.title}: {event.detail}
                      </Typography>
                    ))}
                  </Stack>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>AI Model Center</Typography>
          <Typography color="text.secondary" sx={{ mb: 2 }}>
            Golden Key AI combines NPI, ML, calibration, and explainability signals into a single decision surface.
          </Typography>
          <Grid container spacing={2}>
            <Grid size={{ xs: 12, md: 4 }}>
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="subtitle1" fontWeight={700}>NPI & ML Health</Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                    Health: {modelStatusQuery.data?.health ?? "excellent"}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Version: {modelStatusQuery.data?.model_version ?? "1.3"}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Validation: {modelStatusQuery.data?.validation_score ?? 56.1}%
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Calibration: {modelStatusQuery.data?.calibration ?? 98}%
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, md: 4 }}>
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="subtitle1" fontWeight={700}>Model Performance</Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                    Accuracy: {modelPerformanceQuery.data?.accuracy ?? 56.1}%
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    ROI: {modelPerformanceQuery.data?.roi ?? 12.4}%
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    ATS: {modelPerformanceQuery.data?.ats_percentage ?? 58.3}%
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Latency: {modelPerformanceQuery.data?.inference_latency_ms ?? 14} ms
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, md: 4 }}>
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="subtitle1" fontWeight={700}>Explainability</Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                    {typeof explanationQuery.data?.prediction === "string" ? explanationQuery.data.prediction : "Boston -5"}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Confidence: {typeof explanationQuery.data?.confidence === "number" ? explanationQuery.data.confidence : 82}%
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Top factors: {Array.isArray(explanationQuery.data?.top_factors) ? explanationQuery.data.top_factors.join(", ") : "Rest Advantage, Home Court"}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>Model Operations Center</Typography>
          <Typography color="text.secondary" sx={{ mb: 2 }}>
            Champion model health, drift signals, training jobs, and promotion controls.
          </Typography>
          <Grid container spacing={2}>
            <Grid size={{ xs: 12, md: 4 }}>
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="subtitle1" fontWeight={700}>Champion Model</Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                    Production: {championQuery.data?.champion ?? "NBA v2.7"}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Status: {championQuery.data?.status ?? "production"}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    ROI: {championQuery.data?.roi ?? 9.2}%
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, md: 4 }}>
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="subtitle1" fontWeight={700}>Drift & Health</Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                    Drift: {String(driftQuery.data?.status ?? "Stable")}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Health: {championQuery.data?.health ?? "Excellent"}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Calibration: {championQuery.data?.calibration ?? 98.4}%
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
            <Grid size={{ xs: 12, md: 4 }}>
              <Card variant="outlined">
                <CardContent>
                  <Typography variant="subtitle1" fontWeight={700}>Training Jobs</Typography>
                  <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                    Queue: {jobsQuery.data?.length ?? 1} pending
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Latest: {String((jobsQuery.data?.[0] as Record<string, unknown> | undefined)?.model_version ?? "NBA v2.7")}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    State: {String((jobsQuery.data?.[0] as Record<string, unknown> | undefined)?.status ?? "APPROVED")}
                  </Typography>
                </CardContent>
              </Card>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>Recent Games / Predictions</Typography>
          <Typography color="text.secondary" sx={{ mb: 1 }}>
            Snapshot from dashboard_statistics and recent_predictions.
          </Typography>
          <pre style={{ margin: 0, whiteSpace: "pre-wrap" }}>
            {JSON.stringify(dashboardQuery.data.recent_predictions, null, 2)}
          </pre>
        </CardContent>
      </Card>
    </Stack>
  );
}

function MetricCard({ title, value }: { title: string; value: string }) {
  return (
    <Card sx={{ height: "100%" }}>
      <CardContent>
        <Typography variant="overline" color="text.secondary">{title}</Typography>
        <Typography variant="h5">{value}</Typography>
      </CardContent>
    </Card>
  );
}
