import { Card, CardContent, Grid2 as Grid, Stack, Typography } from "@mui/material";
import React from "react";

export default function EnterprisePage() {
  return (
    <Stack spacing={2}>
      <Stack spacing={0.5}>
        <Typography variant="h4">Enterprise Dashboard</Typography>
        <Typography color="text.secondary">Organization-grade research, analytics, API usage, and team operations.</Typography>
      </Stack>

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 4 }}>
          <Card><CardContent><Typography variant="overline">Organization</Typography><Typography variant="h5">Elite Sports Analytics</Typography></CardContent></Card>
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <Card><CardContent><Typography variant="overline">Active Models</Typography><Typography variant="h4">18</Typography></CardContent></Card>
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <Card><CardContent><Typography variant="overline">API Calls</Typography><Typography variant="h4">2.4M</Typography></CardContent></Card>
        </Grid>
      </Grid>

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 6 }}><Card><CardContent><Typography variant="h6">Overview</Typography><Typography color="text.secondary">Enterprise research and executive reporting at a glance.</Typography></CardContent></Card></Grid>
        <Grid size={{ xs: 12, md: 6 }}><Card><CardContent><Typography variant="h6">Analytics</Typography><Typography color="text.secondary">Model accuracy, ROI reports, and activity breakdowns.</Typography></CardContent></Card></Grid>
        <Grid size={{ xs: 12, md: 6 }}><Card><CardContent><Typography variant="h6">Research</Typography><Typography color="text.secondary">Shared experiments, approvals, and version history.</Typography></CardContent></Card></Grid>
        <Grid size={{ xs: 12, md: 6 }}><Card><CardContent><Typography variant="h6">API Usage</Typography><Typography color="text.secondary">Rate limits, permissions, and auditability.</Typography></CardContent></Card></Grid>
        <Grid size={{ xs: 12, md: 6 }}><Card><CardContent><Typography variant="h6">Users</Typography><Typography color="text.secondary">Researchers, analysts, admins, and API users.</Typography></CardContent></Card></Grid>
        <Grid size={{ xs: 12, md: 6 }}><Card><CardContent><Typography variant="h6">Reports</Typography><Typography color="text.secondary">Performance, risk, research, and ROI reporting.</Typography></CardContent></Card></Grid>
      </Grid>
    </Stack>
  );
}
