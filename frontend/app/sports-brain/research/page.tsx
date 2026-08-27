import { Card, CardContent, Stack, Typography } from "@mui/material";
import React from "react";

export default function SportsBrainResearchPage() {
  return (
    <Stack spacing={2}>
      <Typography variant="h4">Research</Typography>
      <Card>
        <CardContent>
          <Typography>Cross-sport finding: Physical fatigue impacts performance across sports.</Typography>
        </CardContent>
      </Card>
    </Stack>
  );
}
