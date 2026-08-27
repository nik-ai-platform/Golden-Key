import { Card, CardContent, Grid2 as Grid, Stack, Typography } from "@mui/material";
import React from "react";

export default function AIAgentPage() {
  return (
    <Stack spacing={2}>
      <Stack spacing={0.5}>
        <Typography variant="h4">Decision Agent</Typography>
        <Typography color="text.secondary">Agent health, decision history, rewards, policy versions, and learning progress.</Typography>
      </Stack>

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 4 }}>
          <Card><CardContent><Typography variant="overline">Accuracy</Typography><Typography variant="h4">58.4%</Typography></CardContent></Card>
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <Card><CardContent><Typography variant="overline">Reward Trend</Typography><Typography variant="h5">Improving</Typography></CardContent></Card>
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <Card><CardContent><Typography variant="overline">Policy</Typography><Typography variant="h5">v2.1</Typography></CardContent></Card>
        </Grid>
      </Grid>

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 6 }}><Card><CardContent><Typography variant="h6">Agent Health</Typography><Typography color="text.secondary">Model state and stability checks.</Typography></CardContent></Card></Grid>
        <Grid size={{ xs: 12, md: 6 }}><Card><CardContent><Typography variant="h6">Decision History</Typography><Typography color="text.secondary">Recent decisions and outcomes.</Typography></CardContent></Card></Grid>
        <Grid size={{ xs: 12, md: 6 }}><Card><CardContent><Typography variant="h6">Reward Performance</Typography><Typography color="text.secondary">Decision quality over time.</Typography></CardContent></Card></Grid>
        <Grid size={{ xs: 12, md: 6 }}><Card><CardContent><Typography variant="h6">Policy Versions</Typography><Typography color="text.secondary">Rule updates and approval states.</Typography></CardContent></Card></Grid>
        <Grid size={{ xs: 12 }}><Card><CardContent><Typography variant="h6">Learning Progress</Typography><Typography color="text.secondary">Lessons learned from environments and outcomes.</Typography></CardContent></Card></Grid>
      </Grid>
    </Stack>
  );
}
