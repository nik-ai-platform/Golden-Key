import { Card, CardContent, Chip, Grid2 as Grid, Stack, Typography } from "@mui/material";
import React from "react";

export default function ResearchAgentPage() {
  return (
    <Stack spacing={2}>
      <Stack spacing={0.5}>
        <Typography variant="h4">Golden Key Research Agent</Typography>
        <Typography color="text.secondary">Launch automated experiments, review discoveries, and approve validated edges.</Typography>
      </Stack>

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 4 }}>
          <Card>
            <CardContent>
              <Typography variant="overline">Running</Typography>
              <Typography variant="h4">14</Typography>
              <Typography color="text.secondary">Research experiments in flight</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <Card>
            <CardContent>
              <Typography variant="overline">Discoveries</Typography>
              <Typography variant="h4">3</Typography>
              <Typography color="text.secondary">New variable relationships uncovered</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <Card>
            <CardContent>
              <Typography variant="overline">Awaiting Review</Typography>
              <Typography variant="h4">2</Typography>
              <Typography color="text.secondary">Findings pending human approval</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      <Card>
        <CardContent>
          <Typography variant="h6">Start Research</Typography>
          <Typography color="text.secondary" sx={{ mb: 1 }}>
            Find new NBA betting edges using rest, travel, market movement, and matchup structure.
          </Typography>
          <Stack direction="row" spacing={1} flexWrap="wrap">
            <Chip label="Queue new job" color="primary" />
            <Chip label="Review hypothesis" />
            <Chip label="Approve strongest pattern" />
          </Stack>
        </CardContent>
      </Card>
    </Stack>
  );
}
