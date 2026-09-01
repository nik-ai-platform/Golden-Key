import CasinoOutlinedIcon from "@mui/icons-material/CasinoOutlined";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Divider,
  Grid2 as Grid,
  Stack,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import { useMutation } from "@tanstack/react-query";
import { useState } from "react";

import {
  optimizeParlay,
  type OptimizedParlay,
  type ParlayLeg,
} from "../services/parlayOptimizerApi";

const legCounts = [2, 4, 6, 8, 10] as const;

function formatAmericanOdds(value: number): string {
  return value > 0 ? `+${value}` : String(value);
}

function titleCase(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1).toLowerCase();
}

function LegCard({ leg, index }: { leg: ParlayLeg; index: number }) {
  return (
    <Card variant="outlined" sx={{ height: "100%", borderRadius: 2 }}>
      <CardContent>
        <Stack direction="row" justifyContent="space-between" spacing={2} alignItems="flex-start">
          <Box sx={{ minWidth: 0 }}>
            <Typography variant="overline" color="text.secondary">
              Leg {index + 1} · {leg.sport}
            </Typography>
            <Typography variant="h6" fontWeight={800} sx={{ overflowWrap: "anywhere" }}>
              {leg.display_selection}
            </Typography>
          </Box>
          <Chip label={titleCase(leg.market)} color="secondary" size="small" />
        </Stack>

        <Grid container spacing={1.5} sx={{ mt: 1.5 }}>
          {[
            ["NPI", leg.npi_score],
            ["Confidence", `${leg.confidence_score}%`],
            ["Edge", `${leg.projected_edge}%`],
            ["Parlay Score", leg.parlay_score],
          ].map(([label, value]) => (
            <Grid key={label} size={{ xs: 6, sm: 3 }}>
              <Typography variant="caption" color="text.secondary">{label}</Typography>
              <Typography fontWeight={700}>{value}</Typography>
            </Grid>
          ))}
        </Grid>

        <Divider sx={{ my: 2 }} />
        <Typography variant="subtitle2">Why it qualified</Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
          {leg.reasoning || "Golden Key model signals align on this selection."}
        </Typography>
        <Typography variant="caption" color="text.secondary" sx={{ display: "block", mt: 1.5 }}>
          {leg.sportsbook} · {formatAmericanOdds(leg.american_odds)}
        </Typography>
      </CardContent>
    </Card>
  );
}

function ParlayProfile({ parlay }: { parlay: OptimizedParlay }) {
  const metrics = [
    ["Average NPI", parlay.average_npi],
    ["Average Confidence", `${parlay.average_confidence}%`],
    ["Average Edge", `${parlay.average_projected_edge}%`],
    ["Combined Odds", formatAmericanOdds(parlay.combined_american_odds)],
    ["Risk", titleCase(parlay.risk_level)],
  ];

  return (
    <Box sx={{ borderTop: "1px solid", borderColor: "divider", pt: 3 }}>
      <Typography variant="h5" fontWeight={800}>Parlay Profile</Typography>
      <Grid container spacing={2} sx={{ mt: 0.5 }}>
        {metrics.map(([label, value]) => (
          <Grid key={label} size={{ xs: 6, md: 2.4 }}>
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
    </Box>
  );
}

export function ParlayOptimizerPage() {
  const [legCount, setLegCount] = useState<number>(6);
  const mutation = useMutation({
    mutationFn: () => optimizeParlay(legCount),
  });

  return (
    <Stack spacing={4}>
      <Box>
        <Typography variant="h4" fontWeight={800}>Parlay Optimizer</Typography>
        <Typography color="text.secondary" sx={{ mt: 1 }}>
          Build a diversified parlay from current Golden Key predictions.
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

      {mutation.isError ? (
        <Alert severity="info">
          No qualified parlay is available for that leg count right now.
        </Alert>
      ) : null}

      {mutation.data ? (
        <Stack spacing={3}>
          <Box>
            <Typography variant="overline" color="secondary.main" fontWeight={800}>
              Golden Key
            </Typography>
            <Typography variant="h5" fontWeight={800}>
              {mutation.data.leg_count}-Leg Optimized Parlay
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