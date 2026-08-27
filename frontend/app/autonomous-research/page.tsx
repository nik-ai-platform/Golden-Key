import { Card, CardContent, Grid2 as Grid, Stack, Typography } from "@mui/material";
import React from "react";

export default function AutonomousResearchPage() {
  return (
    <Stack spacing={2}>
      <Stack spacing={0.5}>
        <Typography variant="h4">Golden Key Discovery Engine</Typography>
        <Typography color="text.secondary">Self-directed research missions, autonomous experimentation, and human-validated improvements.</Typography>
      </Stack>

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 4 }}>
          <Card>
            <CardContent>
              <Typography variant="overline">New Findings</Typography>
              <Typography variant="h4">12</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <Card>
            <CardContent>
              <Typography variant="overline">Experiments Running</Typography>
              <Typography variant="h4">8</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <Card>
            <CardContent>
              <Typography variant="overline">Pending Review</Typography>
              <Typography variant="h4">3</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Stack>
  );
}
