import { Alert, Box, Button, Card, CardContent, LinearProgress, MenuItem, Stack, TextField, Typography } from "@mui/material";
import { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";

import { useAuth } from "../hooks/useAuth";
import { completeOnboarding, setBankrollSettings, setFavoriteSports, setRiskProfile } from "../services/onboardingService";

const RISK_OPTIONS = ["CONSERVATIVE", "MODERATE", "AGGRESSIVE"];

const STEPS = [
  "Verify Email",
  "Choose Favorite Sports",
  "Risk Profile",
  "Bankroll Settings",
  "Finish",
];

export function OnboardingPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [stepIndex, setStepIndex] = useState(0);
  const [sportsInput, setSportsInput] = useState("NBA,NFL");
  const [riskLevel, setRiskLevel] = useState("MODERATE");
  const [bankroll, setBankroll] = useState("5000");
  const [unitPercent, setUnitPercent] = useState("1.0");
  const [maxDailyRisk, setMaxDailyRisk] = useState("5.0");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const progress = useMemo(() => ((stepIndex + 1) / STEPS.length) * 100, [stepIndex]);

  if (!user) {
    return (
      <Box p={3}>
        <Alert severity="warning">Sign in first to complete onboarding.</Alert>
      </Box>
    );
  }

  const userId = user.id;

  async function nextStep() {
    setSaving(true);
    setError(null);
    setMessage(null);

    try {
      if (stepIndex === 1) {
        const sports = sportsInput.split(",").map((entry) => entry.trim()).filter(Boolean);
        await setFavoriteSports(userId, sports);
      }

      if (stepIndex === 2) {
        await setRiskProfile(userId, riskLevel);
      }

      if (stepIndex === 3) {
        await setBankrollSettings(userId, Number(bankroll), Number(unitPercent), Number(maxDailyRisk));
      }

      if (stepIndex === STEPS.length - 1) {
        await completeOnboarding(userId);
        navigate("/dashboard", { replace: true });
        return;
      }

      setStepIndex((current) => current + 1);
      setMessage("Step saved.");
    } catch {
      setError("Unable to save onboarding step. Please try again.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Box sx={{ minHeight: "100vh", display: "grid", placeItems: "center", p: 2, background: "linear-gradient(160deg, #e0f2fe 0%, #f8fafc 45%, #fef3c7 100%)" }}>
      <Card sx={{ width: "100%", maxWidth: 760 }}>
        <CardContent>
          <Stack spacing={2.5}>
            <Typography variant="h4">Welcome to Golden Key</Typography>
            <Typography color="text.secondary">Step {stepIndex + 1} of {STEPS.length}: {STEPS[stepIndex]}</Typography>
            <LinearProgress variant="determinate" value={progress} />

            {message && <Alert severity="success">{message}</Alert>}
            {error && <Alert severity="error">{error}</Alert>}

            {stepIndex === 0 && (
              <Alert severity="info">Verify your email from your inbox, then continue.</Alert>
            )}

            {stepIndex === 1 && (
              <TextField
                label="Favorite Sports"
                helperText="Comma-separated, for example: NBA, NFL"
                value={sportsInput}
                onChange={(event) => setSportsInput(event.target.value)}
              />
            )}

            {stepIndex === 2 && (
              <TextField select label="Risk Profile" value={riskLevel} onChange={(event) => setRiskLevel(event.target.value)}>
                {RISK_OPTIONS.map((option) => (
                  <MenuItem key={option} value={option}>{option}</MenuItem>
                ))}
              </TextField>
            )}

            {stepIndex === 3 && (
              <Stack spacing={1.5}>
                <TextField label="Starting Bankroll" type="number" value={bankroll} onChange={(event) => setBankroll(event.target.value)} />
                <TextField label="Unit Size (%)" type="number" value={unitPercent} onChange={(event) => setUnitPercent(event.target.value)} />
                <TextField label="Max Daily Risk (%)" type="number" value={maxDailyRisk} onChange={(event) => setMaxDailyRisk(event.target.value)} />
              </Stack>
            )}

            {stepIndex === 4 && (
              <Alert severity="success">Your profile is configured. Continue to dashboard.</Alert>
            )}

            <Stack direction="row" spacing={1.5} justifyContent="space-between">
              <Button disabled={saving || stepIndex === 0} onClick={() => setStepIndex((current) => Math.max(0, current - 1))}>Back</Button>
              <Button variant="contained" disabled={saving} onClick={nextStep}>{saving ? "Saving..." : stepIndex === STEPS.length - 1 ? "Go To Dashboard" : "Continue"}</Button>
            </Stack>
          </Stack>
        </CardContent>
      </Card>
    </Box>
  );
}
