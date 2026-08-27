import { Card, CardContent, Stack, Typography } from "@mui/material";
import React from "react";

export default function SportsBrainAskAIPage() {
  return (
    <Stack spacing={2}>
      <Typography variant="h4">Ask AI</Typography>
      <Card>
        <CardContent>
          <Typography>Why is this team undervalued?</Typography>
          <Typography color="text.secondary">Potential value opportunity based on metrics and simulation alignment.</Typography>
        </CardContent>
      </Card>
    </Stack>
  );
}
