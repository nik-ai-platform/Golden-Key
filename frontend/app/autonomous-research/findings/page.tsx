import { Card, CardContent, Stack, Typography } from "@mui/material";
import React from "react";

export default function AutonomousResearchFindingsPage() {
  return (
    <Stack spacing={2}>
      <Typography variant="h4">AI Findings</Typography>
      <Card>
        <CardContent>
          <Typography>Home advantage model outdated.</Typography>
          <Typography color="text.secondary">Research needed: New venue impact analysis.</Typography>
        </CardContent>
      </Card>
    </Stack>
  );
}
