import { Card, CardContent, Stack, Typography } from "@mui/material";
import React from "react";

export default function SportsBrainReasoningPage() {
  return (
    <Stack spacing={2}>
      <Typography variant="h4">Reasoning</Typography>
      <Card>
        <CardContent>
          <Typography>1. Offensive efficiency exceeds market expectation.</Typography>
          <Typography>2. Defensive matchup favors the team.</Typography>
          <Typography>3. Simulation probability exceeds implied odds.</Typography>
        </CardContent>
      </Card>
    </Stack>
  );
}
