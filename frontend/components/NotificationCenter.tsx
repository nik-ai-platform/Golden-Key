import React from "react";
import { Card, CardContent, Chip, Stack, Typography } from "@mui/material";

const alerts = [
  "New Prediction",
  "Model Update",
  "Risk Warning",
  "Portfolio Alert",
  "Research Discovery",
];

export default function NotificationCenter() {
  return (
    <Card>
      <CardContent>
        <Typography variant="h6" sx={{ mb: 1.5 }}>Notifications</Typography>
        <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
          {alerts.map((alert) => (
            <Chip key={alert} label={alert} color="primary" variant="outlined" />
          ))}
        </Stack>
      </CardContent>
    </Card>
  );
}
