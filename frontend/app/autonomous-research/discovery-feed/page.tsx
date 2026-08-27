import { Card, CardContent, Stack, Typography } from "@mui/material";
import React from "react";

export default function AutonomousResearchDiscoveryFeedPage() {
  return (
    <Stack spacing={2}>
      <Typography variant="h4">Discovery Feed</Typography>
      <Card>
        <CardContent>
          <Typography>New finding: Third road game reduces ATS performance.</Typography>
          <Typography color="text.secondary">Confidence: High</Typography>
        </CardContent>
      </Card>
    </Stack>
  );
}
