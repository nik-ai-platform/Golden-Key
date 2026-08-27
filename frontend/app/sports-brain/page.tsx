import { Card, CardContent, Grid2 as Grid, Stack, Typography } from "@mui/material";
import React from "react";

export default function SportsBrainPage() {
  return (
    <Stack spacing={2}>
      <Stack spacing={0.5}>
        <Typography variant="h4">Golden Key Sports Brain</Typography>
        <Typography color="text.secondary">Unified intelligence layer for cross-sport reasoning, explanation, and strategy planning.</Typography>
      </Stack>

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 4 }}>
          <Card>
            <CardContent>
              <Typography variant="overline">Knowledge</Typography>
              <Typography variant="h4">12.4M</Typography>
              <Typography color="text.secondary">Relationships</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <Card>
            <CardContent>
              <Typography variant="overline">Active Models</Typography>
              <Typography variant="h4">47</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <Card>
            <CardContent>
              <Typography variant="overline">Research Discoveries</Typography>
              <Typography variant="h4">1,284</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Stack>
  );
}
