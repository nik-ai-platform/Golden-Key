import { Card, CardContent, Grid2 as Grid, Stack, Typography } from "@mui/material";
import React from "react";
import SimulationChart from "../../components/SimulationChart";

export default function PortfolioPage() {
  return (
    <Stack spacing={2}>
      <Stack spacing={0.5}>
        <Typography variant="h4">Golden Key Portfolio</Typography>
        <Typography color="text.secondary">Balance, exposure, and AI portfolio recommendations.</Typography>
      </Stack>

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 3 }}>
          <Card><CardContent><Typography variant="overline">Balance</Typography><Typography variant="h4">$5,425</Typography></CardContent></Card>
        </Grid>
        <Grid size={{ xs: 12, md: 3 }}>
          <Card><CardContent><Typography variant="overline">ROI</Typography><Typography variant="h4">8.5%</Typography></CardContent></Card>
        </Grid>
        <Grid size={{ xs: 12, md: 3 }}>
          <Card><CardContent><Typography variant="overline">Risk Score</Typography><Typography variant="h4">42/100</Typography></CardContent></Card>
        </Grid>
        <Grid size={{ xs: 12, md: 3 }}>
          <Card><CardContent><Typography variant="overline">Active Positions</Typography><Typography variant="h6">12 Open Bets</Typography></CardContent></Card>
        </Grid>
      </Grid>

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Typography variant="h6">Positions</Typography>
              <Typography color="text.secondary">Celtics -4 | Stake $100 | Confidence 84%</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Typography variant="h6">Risk</Typography>
              <Typography color="text.secondary">Moderate concentration in NBA ATS markets.</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Typography variant="h6">Performance</Typography>
              <Typography color="text.secondary">NBA Underdogs contributed +72% of ROI.</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Typography variant="h6">AI Coach</Typography>
              <Typography color="text.secondary">Your strongest edge is NBA ATS. Your largest weakness is overexposure to favorites.</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12 }}>
          <SimulationChart teamA="Portfolio Base" teamB="Portfolio Upside" teamAWinProbability={58} projectedScore="$7,275-$4,980" variance="Controlled" />
        </Grid>
      </Grid>
    </Stack>
  );
}

