import { Card, CardContent, Stack, Typography } from "@mui/material";
import React from "react";

export default function SportsBrainInsightsPage() {
  return (
    <Stack spacing={2}>
      <Typography variant="h4">Insights</Typography>
      <Card>
        <CardContent>
          <Typography>Context signal: Playoffs increase intensity and amplify matchup edges.</Typography>
        </CardContent>
      </Card>
    </Stack>
  );
}
