import { Stack, Typography } from "@mui/material";

export function ConfidenceBadge({ confidence }: { confidence: number | null }) {
  if (confidence == null) return <Typography color="text.secondary">No confidence score</Typography>;

  const label = confidence >= 80 ? "High" : confidence >= 70 ? "Strong" : confidence >= 60 ? "Moderate" : "Watch";
  return (
    <Stack spacing={0.25} alignItems={{ xs: "flex-start", sm: "flex-end" }}>
      <Typography variant="overline" color="text.secondary">Confidence</Typography>
      <Stack direction="row" spacing={1} alignItems="baseline">
        <Typography variant="h5">{confidence.toFixed(1)}%</Typography>
        <Typography variant="caption" color="text.secondary">{label}</Typography>
      </Stack>
    </Stack>
  );
}
