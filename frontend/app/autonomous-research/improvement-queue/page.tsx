import { Card, CardContent, Stack, Typography } from "@mui/material";
import React from "react";

export default function AutonomousResearchImprovementQueuePage() {
  return (
    <Stack spacing={2}>
      <Typography variant="h4">Improvement Queue</Typography>
      <Card>
        <CardContent>
          <Typography>Model: NPI NBA</Typography>
          <Typography color="text.secondary">Proposal: Increase rest weight +3 | Expected: +1.2% ATS</Typography>
        </CardContent>
      </Card>
    </Stack>
  );
}
