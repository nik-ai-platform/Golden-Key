import { Card, CardContent, Stack, Typography } from "@mui/material";
import React from "react";

export default function ResearchAgentBacktestPage() {
  return (
    <Stack spacing={2}>
      <Typography variant="h4">Backtesting Laboratory</Typography>
      <Card>
        <CardContent>
          <Typography variant="h6">Home Favorites -4.5</Typography>
          <Typography color="text.secondary">Games: 842 • ATS: 56.3% • ROI: +11.4%</Typography>
        </CardContent>
      </Card>
    </Stack>
  );
}
