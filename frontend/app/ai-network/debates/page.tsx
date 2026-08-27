import { Card, CardContent, Stack, Typography } from "@mui/material";
import React from "react";

export default function AINetworkDebatesPage() {
  return (
    <Stack spacing={2}>
      <Typography variant="h4">Agent Debates</Typography>
      <Card><CardContent><Typography>Does edge justify risk?</Typography></CardContent></Card>
    </Stack>
  );
}
