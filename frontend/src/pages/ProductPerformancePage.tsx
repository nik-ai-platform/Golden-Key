import {
  Box,
  Card,
  CardContent,
  Grid2 as Grid,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { EmptyState } from "../components/EmptyState";
import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { getPerformanceIntelligence } from "../services/productApi";
import type { PerformanceIntelligenceBreakdown } from "../types/product";

type PeriodDays = 7 | 30 | 90;

const periodOptions: PeriodDays[] = [7, 30, 90];
const marketOrder = ["SPREAD", "MONEYLINE", "TOTAL"];
const sportOrder = ["NFL", "NBA", "NCAAF", "NCAAB", "WNBA"];
const sideOrder = ["Favorite", "Underdog", "Other", "Unknown"];

function formatSigned(value: number, suffix = "") {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(2)}${suffix}`;
}

function formatSegment(value: string): string {
  if (marketOrder.includes(value.toUpperCase())) {
    const normalized = value.toLowerCase();
    return normalized.charAt(0).toUpperCase() + normalized.slice(1);
  }
  return value;
}

function orderRows(
  rows: PerformanceIntelligenceBreakdown[],
  order: string[],
): PerformanceIntelligenceBreakdown[] {
  return [...rows].sort((left, right) => {
    const leftIndex = order.indexOf(left.key);
    const rightIndex = order.indexOf(right.key);
    const leftRank = leftIndex === -1 ? order.length : leftIndex;
    const rightRank = rightIndex === -1 ? order.length : rightIndex;
    return leftRank - rightRank || left.key.localeCompare(right.key);
  });
}

function BreakdownTable({
  title,
  rows,
}: {
  title?: string;
  rows: PerformanceIntelligenceBreakdown[];
}) {
  return (
    <Stack spacing={1.25} sx={{ minWidth: 0, width: "100%" }}>
      {title ? (
        <Typography variant="h6" fontWeight={700}>
          {title}
        </Typography>
      ) : null}
      <TableContainer
        sx={{
          border: 1,
          borderColor: "divider",
          borderRadius: 2,
          overflowX: "auto",
          width: "100%",
        }}
      >
        <Table size="small" aria-label={`${title ?? "Performance"} table`} sx={{ minWidth: 640 }}>
          <TableHead>
            <TableRow>
              <TableCell>Segment</TableCell>
              <TableCell align="right">Bets</TableCell>
              <TableCell align="right">W-L-P</TableCell>
              <TableCell align="right">Win Rate</TableCell>
              <TableCell align="right">Units</TableCell>
              <TableCell align="right">ROI</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.length ? (
              rows.map((row) => (
                <TableRow key={row.key}>
                  <TableCell component="th" scope="row" sx={{ fontWeight: 700 }}>
                    {formatSegment(row.key)}
                  </TableCell>
                  <TableCell align="right">{row.total_bets}</TableCell>
                  <TableCell align="right">
                    {row.wins}-{row.losses}-{row.pushes}
                  </TableCell>
                  <TableCell align="right">{row.win_rate.toFixed(2)}%</TableCell>
                  <TableCell align="right">{formatSigned(row.units_won, " units")}</TableCell>
                  <TableCell align="right">{formatSigned(row.roi, "%")}</TableCell>
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell colSpan={6}>No settled predictions in this period.</TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Stack>
  );
}

export function ProductPerformancePage() {
  const [periodDays, setPeriodDays] = useState<PeriodDays>(30);
  const query = useQuery({
    queryKey: ["product", "performance-intelligence", periodDays],
    queryFn: () => getPerformanceIntelligence(periodDays),
  });

  return (
    <Stack spacing={4} sx={{ minWidth: 0, width: "100%" }}>
      <Stack
        direction={{ xs: "column", sm: "row" }}
        justifyContent="space-between"
        alignItems={{ sm: "flex-end" }}
        spacing={2}
        sx={{ minWidth: 0, width: "100%" }}
      >
        <Box>
          <Typography variant="h4" fontWeight={700}>
            Performance Intelligence
          </Typography>
          <Typography color="text.secondary" sx={{ mt: 1 }}>
            Settled model performance across markets, sports, and signal strength.
          </Typography>
        </Box>

        <ToggleButtonGroup
          value={periodDays}
          exclusive
          size="small"
          aria-label="Performance period"
          onChange={(_, value: PeriodDays | null) => {
            if (value !== null) setPeriodDays(value);
          }}
        >
          {periodOptions.map((days) => (
            <ToggleButton key={days} value={days} aria-label={`${days} days`}>
              {days} Days
            </ToggleButton>
          ))}
        </ToggleButtonGroup>
      </Stack>

      {query.isLoading ? <LoadingState message="Loading performance intelligence..." /> : null}

      {query.isError ? (
        <ErrorState
          kind="network"
          detail="Unable to load performance intelligence right now."
          onRetry={() => void query.refetch()}
        />
      ) : null}

      {query.data && !query.data.overall.total_bets ? (
        <EmptyState title="No settled predictions in this period." />
      ) : null}

      {query.data?.overall.total_bets ? (
        <>
          <Stack component="section" aria-labelledby="overall-performance" spacing={2} sx={{ minWidth: 0, width: "100%" }}>
            <Typography id="overall-performance" variant="h5" fontWeight={700}>
              Overall
            </Typography>
            <Box
              data-testid="overall-metrics-grid"
              sx={{
                display: "grid",
                gap: 2,
                gridTemplateColumns: {
                  xs: "1fr",
                  sm: "repeat(2, minmax(0, 1fr))",
                  md: "repeat(4, minmax(0, 1fr))",
                },
                minWidth: 0,
                width: "100%",
              }}
            >
              {[
                ["Total Bets", String(query.data.overall.total_bets)],
                ["Win Rate", `${query.data.overall.win_rate.toFixed(2)}%`],
                ["Units Won", formatSigned(query.data.overall.units_won, " units")],
                ["ROI", formatSigned(query.data.overall.roi, "%")],
              ].map(([label, value]) => (
                <Box key={label} sx={{ minWidth: 0 }}>
                  <Card variant="outlined" sx={{ borderRadius: 2, height: "100%" }}>
                    <CardContent>
                      <Typography variant="body2" color="text.secondary">
                        {label}
                      </Typography>
                      <Typography variant="h5" fontWeight={700} sx={{ mt: 0.75 }}>
                        {value}
                      </Typography>
                    </CardContent>
                  </Card>
                </Box>
              ))}
            </Box>
          </Stack>

          <Stack component="section" aria-labelledby="market-performance" spacing={2} sx={{ minWidth: 0, width: "100%" }}>
            <Typography id="market-performance" variant="h5" fontWeight={700}>
              Market Performance
            </Typography>
            <BreakdownTable rows={orderRows(query.data.by_market, marketOrder)} />
          </Stack>

          <Stack component="section" aria-labelledby="model-strength" spacing={2} sx={{ minWidth: 0, width: "100%" }}>
            <Typography id="model-strength" variant="h5" fontWeight={700}>
              Model Strength
            </Typography>
            <Grid container spacing={3} sx={{ minWidth: 0, width: "100%" }}>
              <Grid size={{ xs: 12 }} sx={{ minWidth: 0 }}>
                <BreakdownTable title="NPI Bands" rows={query.data.by_npi_band} />
              </Grid>
              <Grid size={{ xs: 12 }} sx={{ minWidth: 0 }}>
                <BreakdownTable title="Confidence Bands" rows={query.data.by_confidence_band} />
              </Grid>
              <Grid size={{ xs: 12 }} sx={{ minWidth: 0 }}>
                <BreakdownTable title="Odds Bands" rows={query.data.by_odds_band} />
              </Grid>
            </Grid>
          </Stack>

          <Stack component="section" aria-labelledby="sport-performance" spacing={2} sx={{ minWidth: 0, width: "100%" }}>
            <Typography id="sport-performance" variant="h5" fontWeight={700}>
              Sport Performance
            </Typography>
            <BreakdownTable rows={orderRows(query.data.by_sport, sportOrder)} />
          </Stack>

          <Stack component="section" aria-labelledby="bet-profile" spacing={2} sx={{ minWidth: 0, width: "100%" }}>
            <Typography id="bet-profile" variant="h5" fontWeight={700}>
              Bet Profile
            </Typography>
            <BreakdownTable rows={orderRows(query.data.by_side_type, sideOrder)} />
          </Stack>

          <Stack component="section" aria-labelledby="model-version" spacing={2} sx={{ minWidth: 0, width: "100%" }}>
            <Typography id="model-version" variant="h5" fontWeight={700}>
              Model Version
            </Typography>
            <BreakdownTable rows={query.data.by_model_version} />
          </Stack>
        </>
      ) : null}
    </Stack>
  );
}