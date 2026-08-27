import { Card, CardContent, Stack, Typography } from "@mui/material";
import React from "react";

export default function AutonomousResearchKnowledgeGraphPage() {
  return (
    <Stack spacing={2}>
      <Typography variant="h4">Knowledge Graph</Typography>
      <Card>
        <CardContent>
          <Typography>Back-to-back → Fatigue → Lower Shooting % → Under Performance</Typography>
        </CardContent>
      </Card>
    </Stack>
  );
}
