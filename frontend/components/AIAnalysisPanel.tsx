import React from "react";
import { Card, CardContent, List, ListItem, ListItemText, Typography } from "@mui/material";

type AIAnalysisPanelProps = {
  title?: string;
  reasons: string[];
  mainRisk: string;
};

export default function AIAnalysisPanel({ title = "Why this pick?", reasons, mainRisk }: AIAnalysisPanelProps) {
  return (
    <Card>
      <CardContent>
        <Typography variant="h6" sx={{ mb: 1 }}>Golden Key Analysis</Typography>
        <Typography color="text.secondary" sx={{ mb: 1.5 }}>{title}</Typography>
        <List dense disablePadding>
          {reasons.map((reason, index) => (
            <ListItem key={reason} disableGutters>
              <ListItemText primary={`${index + 1}. ${reason}`} />
            </ListItem>
          ))}
        </List>
        <Typography sx={{ mt: 1.5 }}><strong>Main Risk:</strong> {mainRisk}</Typography>
      </CardContent>
    </Card>
  );
}
