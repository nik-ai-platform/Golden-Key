import { Paper, Typography } from "@mui/material";

interface PredictionMetricProps {
  label: string;
  value: string;
}

export function PredictionMetric({ label, value }: PredictionMetricProps) {
  return (
    <Paper variant="outlined" sx={{ p: 2, minHeight: 86, borderRadius: 2 }}>
      <Typography variant="overline" color="text.secondary">{label}</Typography>
      <Typography variant="h6" sx={{ mt: 0.5, overflowWrap: "anywhere" }}>{value}</Typography>
    </Paper>
  );
}
