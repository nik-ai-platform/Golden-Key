import { Card, CardContent, Stack, Typography } from "@mui/material";
import React from "react";

export default function ResearchAgentSimulatorPage() {
  return (
    <Stack spacing={2}>
      <Typography variant="h4">Monte Carlo Simulator</Typography>
      <Card>
        <CardContent>
          <Typography variant="h6">55% win rate</Typography>
          <Typography color="text.secondary">10,000 simulations • Expected ROI: +8% • Worst Case: -12%</Typography>
        </CardContent>
      </Card>
    </Stack>
  );
}
