import { Card, CardContent, Stack, Typography } from "@mui/material";
import React from "react";

export default function AINetworkPerformancePage() {
  return (
    <Stack spacing={2}>
      <Typography variant="h4">Agent Performance</Typography>
      <Card><CardContent><Typography>Simulation Agent Accuracy: 59.2% | Weight: HIGH</Typography></CardContent></Card>
    </Stack>
  );
}
