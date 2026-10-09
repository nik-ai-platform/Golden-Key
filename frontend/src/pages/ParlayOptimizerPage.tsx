import CasinoOutlinedIcon from "@mui/icons-material/CasinoOutlined";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Divider,
  FormControl,
  Grid2 as Grid,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import { useMutation } from "@tanstack/react-query";
import { Link as RouterLink } from "react-router-dom";
import { useState } from "react";

import {
  optimizeParlay,
  type OptimizedParlay,
  type ParlayLeg,
} from "../services/parlayOptimizerApi";
import { customerFacingReasoning, formatConfidence, formatModelProbability, formatProductDate } from "../utils/productFormat";

const legCounts = [2, 4, 6, 8, 10] as const;

type ParlayFailure = {
  severity: "error" | "info";
  message: string;
  action: "retry" | "profile" | "login" | null;
};

function formatAmericanOdds(value: number): string {
  return value > 0 ? `+${value}` : String(value);
}

function titleCase(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1).toLowerCase();
}

function getParlayFailure(error: unknown): ParlayFailure {
  const failure = typeof error === "object" && error !== null ? error : null;
  const status = failure && "status" in failure && typeof failure.status === "number"
    ? failure.status
    : null;
  const message = failure && "message" in failure && typeof failure.message === "string"
    ? failure.message
    : null;

  if (status === 401) {
    return {
      severity: "error",
      message: "Your session has expired or is no longer valid. Sign in again to continue.",
      action: "login",
    };
  }
  if (status === 403) {
    return {
      severity: "error",
      message: "Parlay Optimizer requires active Premium access. Review your subscription in Profile.",
      action: "profile",
    };
  }
  if (status === 422 && message) {
    const insufficientPicks = [
      "not enough qualified predictions",
      "only ",
      "no upcoming picks",
      "the available quoted picks",
      "qualified predictions cannot satisfy",
    ].some((phrase) => message.toLowerCase().startsWith(phrase));
    return {
      severity: insufficientPicks ? "info" : "error",
      message,
      action: insufficientPicks ? null : "retry",
    };
  }
  if (status === 0) {
    return {
      severity: "error",
      message: "Could not reach the optimizer service. Check your connection and try again.",
      action: "retry",
    };
  }
  if (status === 408) {
    return {
      severity: "error",
      message: "The optimizer request timed out. Try again in a moment.",
      action: "retry",
    };
  }
  if (status !== null && status >= 500) {
    return {
      severity: "error",
      message: `The optimizer service encountered a server error (HTTP ${status}). Try again; contact Support if it continues.`,
      action: "retry",
    };
  }
  if (status !== null && status >= 400) {
    return {
      severity: "error",
      message: message || `The request was rejected (HTTP ${status}).`,
      action: "retry",
    };
  }
  return {
    severity: "error",
    message: "The optimizer request failed unexpectedly. Try again; contact Support if it continues.",
    action: "retry",
  };
}

function LegCard({ leg, index }: { leg: ParlayLeg; index: number }) {
  const visibleReasoning = customerFacingReasoning(leg.reasoning);
  const matchup = `${leg.away_team} at ${leg.home_team}`;

  return (
    <Card data-testid="parlay-leg-card" variant="outlined" sx={{ height: "100%", borderRadius: 2 }}>
      <CardContent>
        <Stack direction="row" justifyContent="space-between" spacing={2} alignItems="flex-start">
          <Box sx={{ minWidth: 0 }}>
            <Typography variant="overline" color="text.secondary">
              Leg {index + 1} · {leg.sport}
            </Typography>
            <Typography variant="body2" fontWeight={700} sx={{ overflowWrap: "anywhere" }}>
              {matchup}
            </Typography>
            <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 0.25 }}>
              {formatProductDate(leg.game_date)}
            </Typography>
            <Typography variant="h6" fontWeight={800} sx={{ mt: 0.75, overflowWrap: "anywhere" }}>
              {leg.display_selection}
            </Typography>
          </Box>
          <Chip label={titleCase(leg.market)} color="secondary" size="small" />
        </Stack>

        <Grid container spacing={1.5} sx={{ mt: 1.5 }}>
          {[
            ["NPI", leg.npi_score],
            ["Confidence Rating", formatConfidence(leg.confidence_score)],
            ["Model Probability", formatModelProbability(leg.simulation_probability)],
          ].map(([label, value]) => (
            <Grid key={label} size={{ xs: 6, sm: 4 }}>
              <Typography variant="caption" color="text.secondary">{label}</Typography>
              <Typography fontWeight={700}>{value}</Typography>
            </Grid>
          ))}
        </Grid>

        <Divider sx={{ my: 2 }} />
        <Typography variant="subtitle2">Why selected</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
          {leg.selection_reason || "Included in the highest-scoring valid combination under the optimizer's distinct-game and market-mix rules."}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          {visibleReasoning || "Bear A Hand Sports model signals align on this selection."}
        </Typography>
        <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1.5 }}>
          {leg.sportsbook} · {formatAmericanOdds(leg.american_odds)}
        </Typography>
        <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 0.25 }}>
          Quoted {formatProductDate(leg.odds_observed_at)}
        </Typography>
      </CardContent>
    </Card>
  );
}

function ParlayProfile({ parlay }: { parlay: OptimizedParlay }) {
  const metrics = [
    ["Average NPI", parlay.average_npi],
    ["Average Confidence Rating", formatConfidence(parlay.average_confidence)],
    ["Combined Odds", formatAmericanOdds(parlay.combined_american_odds)],
    ["Risk", parlay.risk_level ? titleCase(parlay.risk_level) : "Not rated"],
  ];

  return (
    <Box sx={{ borderTop: "1px solid", borderColor: "divider", pt: 3 }}>
      <Typography variant="h5" fontWeight={800}>Parlay Profile</Typography>
      <Grid container spacing={2} sx={{ mt: 0.5 }}>
        {metrics.map(([label, value]) => (
          <Grid key={label} size={{ xs: 6, md: 3 }}>
            <Typography variant="body2" color="text.secondary">{label}</Typography>
            <Typography variant="h6" fontWeight={800}>{value}</Typography>
          </Grid>
        ))}
      </Grid>
      <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" sx={{ mt: 2 }}>
        <Chip label={`Spreads: ${parlay.market_mix.spread}`} variant="outlined" />
        <Chip label={`Totals: ${parlay.market_mix.total}`} variant="outlined" />
        <Chip label={`Moneylines: ${parlay.market_mix.moneyline}`} variant="outlined" />
      </Stack>
      <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
        No combined win probability is estimated. Multiplying leg probabilities assumes independence; distinct games avoid same-game conflicts but do not establish independence across games.
      </Typography>
    </Box>
  );
}

export function ParlayOptimizerPage() {
  const [legCount, setLegCount] = useState<number>(6);
  const [sport, setSport] = useState("");
  const mutation = useMutation({
    mutationFn: () => optimizeParlay(legCount, sport || undefined),
  });
  const parlayFailure = mutation.isError ? getParlayFailure(mutation.error) : null;

  return (
    <Stack spacing={4}>
      <Box>
        <Typography variant="h4" fontWeight={800}>Parlay Optimizer</Typography>
        <Typography color="text.secondary" sx={{ mt: 1 }}>
          Build a diversified parlay from current Bear A Hand Sports predictions.
        </Typography>
      </Box>

      <Stack direction={{ xs: "column", sm: "row" }} spacing={2} alignItems={{ sm: "center" }}>
        <ToggleButtonGroup
          exclusive
          value={legCount}
          onChange={(_, value: number | null) => value && setLegCount(value)}
          aria-label="Parlay leg count"
          sx={{ display: "grid", gridTemplateColumns: "repeat(5, minmax(0, 1fr))", width: { xs: "100%", sm: "auto" } }}
        >
          {legCounts.map((count) => (
            <ToggleButton key={count} value={count} aria-label={`${count} Leg`} sx={{ minWidth: { sm: 72 }, whiteSpace: "nowrap" }}>
              {count} Leg
            </ToggleButton>
          ))}
        </ToggleButtonGroup>
        <FormControl size="small" sx={{ minWidth: { xs: "100%", sm: 160 } }}>
          <InputLabel id="parlay-sport-label">Sport</InputLabel>
          <Select<string>
            labelId="parlay-sport-label"
            value={sport}
            label="Sport"
            onChange={(event) => setSport(event.target.value)}
          >
            <MenuItem value="">All sports</MenuItem>
            {["NFL", "NBA", "NCAAF", "NCAAB", "WNBA"].map((value) => (
              <MenuItem key={value} value={value}>{value}</MenuItem>
            ))}
          </Select>
        </FormControl>
        <Button
          variant="contained"
          size="large"
          startIcon={<CasinoOutlinedIcon />}
          onClick={() => mutation.mutate()}
          disabled={mutation.isPending}
          sx={{ minHeight: 48 }}
        >
          {mutation.isPending ? "Building..." : "Build Best Parlay"}
        </Button>
      </Stack>

      {parlayFailure ? (
        <Alert
          severity={parlayFailure.severity}
          action={
            parlayFailure.action === "retry" ? (
              <Button disabled={mutation.isPending} onClick={() => mutation.mutate()}>Retry</Button>
            ) : parlayFailure.action === "profile" ? (
              <Button component={RouterLink} to="/profile">Profile</Button>
            ) : parlayFailure.action === "login" ? (
              <Button component={RouterLink} to="/login">Sign in</Button>
            ) : undefined
          }
        >
          {parlayFailure.message}
        </Alert>
      ) : null}

      {mutation.data ? (
        <Stack spacing={3}>
          {mutation.data.adjustment_reason ? (
            <Alert severity="info">{mutation.data.adjustment_reason}</Alert>
          ) : null}
          <Box>
            <Typography variant="overline" color="secondary.main" fontWeight={800}>
              Bear A Hand Sports
            </Typography>
            <Typography variant="h5" fontWeight={800}>
              {mutation.data.leg_count}-Leg Optimized Parlay
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
              Optimized from qualifying games in the next {mutation.data.horizon_days} days
              {mutation.data.sport ? ` · ${mutation.data.sport}` : " · All sports"}
            </Typography>
          </Box>
          <Grid container spacing={2}>
            {mutation.data.legs.map((leg, index) => (
              <Grid key={leg.prediction_id} size={{ xs: 12, lg: 6 }}>
                <LegCard leg={leg} index={index} />
              </Grid>
            ))}
          </Grid>
          <ParlayProfile parlay={mutation.data} />
        </Stack>
      ) : null}
    </Stack>
  );
}