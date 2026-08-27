import { Card, CardContent, Stack, Typography } from "@mui/material";
import React from "react";

export default function ResearchAgentReportsPage() {
  return (
    <Stack spacing={2}>
      <Typography variant="h4">Research Reports</Typography>
      <Card>
        <CardContent>
          <Typography variant="h6">AI Research Finding</Typography>
          <Typography color="text.secondary">Pattern: NBA home underdogs + rest advantage • Confidence: Medium</Typography>
        </CardContent>
      </Card>
    </Stack>
  );
}
