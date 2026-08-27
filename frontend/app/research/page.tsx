import React from "react";
import { Card, CardContent, Grid2 as Grid, Stack, Typography } from "@mui/material";

export default function ResearchPage() {
  return (
    <Stack spacing={2.5}>
      <Stack spacing={0.5}>
        <Typography variant="h4">Research Intelligence</Typography>
        <Typography color="text.secondary">AI discoveries, experiments, model updates, and insights.</Typography>
      </Stack>

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Typography variant="h6">AI Discoveries</Typography>
              <Typography sx={{ mt: 1 }}>Road favorites declining after travel.</Typography>
              <Typography color="text.secondary">Impact: NBA Model Update Proposed</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Typography variant="h6">Experiments</Typography>
              <Typography sx={{ mt: 1 }}>Travel Fatigue Model backtest running</Typography>
              <Typography color="text.secondary">Current uplift estimate: +1.8% ROI</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Typography variant="h6">Model Updates</Typography>
              <Typography sx={{ mt: 1 }}>Rest weighting candidate: +3</Typography>
              <Typography color="text.secondary">Pending review and controlled rollout</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <Card>
            <CardContent>
              <Typography variant="h6">Insights</Typography>
              <Typography sx={{ mt: 1 }}>Cross-sport pattern confirms fatigue impact.</Typography>
              <Typography color="text.secondary">NFL/NBA/NCAAB alignment detected</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Stack>
  );
}
