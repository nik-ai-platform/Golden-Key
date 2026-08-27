import { Card, CardContent, Grid2 as Grid, Stack, Typography } from "@mui/material";
import React from "react";

export default function AILearningPage() {
  return (
    <Stack spacing={2}>
      <Stack spacing={0.5}>
        <Typography variant="h4">Golden Key AI Health</Typography>
        <Typography color="text.secondary">Learning overview, model health, suggested improvements, experiments, and versions.</Typography>
      </Stack>

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 4 }}>
          <Card><CardContent><Typography variant="overline">NPI NFL</Typography><Typography variant="h5">Healthy</Typography></CardContent></Card>
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <Card><CardContent><Typography variant="overline">NPI NBA</Typography><Typography variant="h5">Needs Review</Typography></CardContent></Card>
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <Card><CardContent><Typography variant="overline">New Discoveries</Typography><Typography variant="h4">7</Typography></CardContent></Card>
        </Grid>
      </Grid>

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 6 }}><Card><CardContent><Typography variant="h6">Learning Overview</Typography><Typography color="text.secondary">Capture every learning opportunity.</Typography></CardContent></Card></Grid>
        <Grid size={{ xs: 12, md: 6 }}><Card><CardContent><Typography variant="h6">Model Health</Typography><Typography color="text.secondary">Drift, calibration, and performance tracking.</Typography></CardContent></Card></Grid>
        <Grid size={{ xs: 12, md: 6 }}><Card><CardContent><Typography variant="h6">Suggested Improvements</Typography><Typography color="text.secondary">Adaptive NPI changes and validation status.</Typography></CardContent></Card></Grid>
        <Grid size={{ xs: 12, md: 6 }}><Card><CardContent><Typography variant="h6">Experiments</Typography><Typography color="text.secondary">Learning events, feedback loops, and model tests.</Typography></CardContent></Card></Grid>
        <Grid size={{ xs: 12 }}><Card><CardContent><Typography variant="h6">Versions</Typography><Typography color="text.secondary">Model version control and human approval workflow.</Typography></CardContent></Card></Grid>
      </Grid>
    </Stack>
  );
}
