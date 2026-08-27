import { Card, CardContent, Stack, Typography } from "@mui/material";
import React from "react";

export default function SportsBrainKnowledgeMapPage() {
  return (
    <Stack spacing={2}>
      <Typography variant="h4">Knowledge Map</Typography>
      <Card>
        <CardContent>
          <Typography>Teams, Players, Coaches, Strategies, Markets, Conditions, Historical Events, Trends</Typography>
        </CardContent>
      </Card>
    </Stack>
  );
}
