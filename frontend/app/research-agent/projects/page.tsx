import { Card, CardContent, Stack, Typography } from "@mui/material";
import React from "react";

export default function ResearchAgentProjectsPage() {
  return (
    <Stack spacing={2}>
      <Typography variant="h4">Research Projects</Typography>
      <Card>
        <CardContent>
          <Typography variant="h6">NBA Road Underdog Study</Typography>
          <Typography color="text.secondary">Sport: NBA • Market: ATS • Status: Active</Typography>
        </CardContent>
      </Card>
    </Stack>
  );
}
