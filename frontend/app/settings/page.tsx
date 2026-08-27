import React from "react";
import { Card, CardContent, Grid2 as Grid, Stack, Typography } from "@mui/material";

export default function SettingsPage() {
  return (
    <Stack spacing={2.5}>
      <Stack spacing={0.5}>
        <Typography variant="h4">Settings</Typography>
        <Typography color="text.secondary">Sports preferences, risk profile, bankroll, notifications, and AI detail level.</Typography>
      </Stack>
      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 6 }}><Card><CardContent><Typography variant="h6">Sports Preferences</Typography><Typography color="text.secondary">NBA, NFL, NCAAB</Typography></CardContent></Card></Grid>
        <Grid size={{ xs: 12, md: 6 }}><Card><CardContent><Typography variant="h6">Risk Profile</Typography><Typography color="text.secondary">Moderate</Typography></CardContent></Card></Grid>
        <Grid size={{ xs: 12, md: 6 }}><Card><CardContent><Typography variant="h6">Bankroll</Typography><Typography color="text.secondary">$5,425 configured</Typography></CardContent></Card></Grid>
        <Grid size={{ xs: 12, md: 6 }}><Card><CardContent><Typography variant="h6">Notification Preferences</Typography><Typography color="text.secondary">Prediction, model, risk, portfolio, discovery alerts enabled</Typography></CardContent></Card></Grid>
        <Grid size={{ xs: 12 }}><Card><CardContent><Typography variant="h6">AI Detail Level</Typography><Typography color="text.secondary">Analyst depth with concise summaries</Typography></CardContent></Card></Grid>
      </Grid>
    </Stack>
  );
}

