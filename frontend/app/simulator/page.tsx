import { Card, CardContent, Grid2 as Grid, Slider, Stack, Typography } from "@mui/material";
import React from "react";

export default function SimulatorPage() {
  return (
    <Stack spacing={2}>
      <Stack spacing={0.5}>
        <Typography variant="h4">Simulation Dashboard</Typography>
        <Typography color="text.secondary">Run simulations, adjust variables, compare scenarios, and analyze risk.</Typography>
      </Stack>

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Typography variant="h6">Lakers vs Warriors</Typography>
              <Typography color="text.secondary">50,000 simulations</Typography>
              <Typography variant="h3" sx={{ mt: 1 }}>58% / 42%</Typography>
              <Typography color="text.secondary">Most likely score: Lakers 116, Warriors 111</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Typography variant="h6">Adjust Variables</Typography>
              <Stack spacing={2} sx={{ mt: 2 }}>
                <Typography gutterBottom>Weather</Typography>
                <Slider defaultValue={35} />
                <Typography gutterBottom>Injuries</Typography>
                <Slider defaultValue={20} />
                <Typography gutterBottom>Pace</Typography>
                <Slider defaultValue={55} />
              </Stack>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 4 }}>
          <Card><CardContent><Typography variant="h6">Run Simulation</Typography></CardContent></Card>
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <Card><CardContent><Typography variant="h6">Compare Scenarios</Typography></CardContent></Card>
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <Card><CardContent><Typography variant="h6">Analyze Risk</Typography></CardContent></Card>
        </Grid>
      </Grid>
    </Stack>
  );
}
