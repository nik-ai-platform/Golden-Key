import React from "react";
import { Box, LinearProgress, Stack, Typography } from "@mui/material";

type NPIIndicatorProps = {
  score: number;
  label?: string;
};

function getBand(score: number): string {
  if (score < 50) return "Weak";
  if (score < 75) return "Average";
  if (score < 90) return "Strong";
  return "Elite";
}

export default function NPIIndicator({ score, label = "NPI Score" }: NPIIndicatorProps) {
  const normalized = Math.max(0, Math.min(100, score));
  const band = getBand(normalized);
  const color = normalized >= 90 ? "success" : normalized >= 75 ? "primary" : normalized >= 50 ? "warning" : "error";

  return (
    <Box>
      <Stack direction="row" justifyContent="space-between">
        <Typography variant="subtitle2">{label}</Typography>
        <Typography variant="subtitle2">{normalized}</Typography>
      </Stack>
      <LinearProgress variant="determinate" value={normalized} color={color} sx={{ my: 0.75, borderRadius: 5, height: 8 }} />
      <Typography variant="caption" color="text.secondary">{band} Value</Typography>
    </Box>
  );
}
