import { Card, CardContent, Stack, Typography } from "@mui/material";
import React from "react";

export default function AutonomousResearchActiveExperimentsPage() {
  return (
    <Stack spacing={2}>
      <Typography variant="h4">Active Experiments</Typography>
      <Card>
        <CardContent>
          <Typography>Testing: Travel Fatigue Model</Typography>
          <Typography color="text.secondary">Games: 15,000 | Impact: +1.8% ROI</Typography>
        </CardContent>
      </Card>
    </Stack>
  );
}
