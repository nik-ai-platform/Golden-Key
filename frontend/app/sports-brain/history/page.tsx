import { Card, CardContent, Stack, Typography } from "@mui/material";
import React from "react";

export default function SportsBrainHistoryPage() {
  return (
    <Stack spacing={2}>
      <Typography variant="h4">History</Typography>
      <Card>
        <CardContent>
          <Typography>Lesson: Teams resting starters perform worse ATS.</Typography>
        </CardContent>
      </Card>
    </Stack>
  );
}
