import { Card, CardContent, Grid2 as Grid, Stack, Typography } from "@mui/material";
import React from "react";

export default function AINetworkPage() {
  return (
    <Stack spacing={2}>
      <Typography variant="h4">Golden Key AI Council</Typography>
      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 4 }}><Card><CardContent><Typography variant="overline">Active Agents</Typography><Typography variant="h4">7</Typography></CardContent></Card></Grid>
        <Grid size={{ xs: 12, md: 4 }}><Card><CardContent><Typography variant="overline">Consensus Accuracy</Typography><Typography variant="h4">58.9%</Typography></CardContent></Card></Grid>
        <Grid size={{ xs: 12, md: 4 }}><Card><CardContent><Typography variant="overline">Current Debate</Typography><Typography variant="h6">Chiefs vs Bills</Typography></CardContent></Card></Grid>
      </Grid>
    </Stack>
  );
}
