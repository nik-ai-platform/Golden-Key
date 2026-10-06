import { Stack, Typography } from "@mui/material";

export function ConfidenceBadge({ confidence }: { confidence: number | null }) {
  if (confidence == null) return <Typography color="text.secondary">No confidence score</Typography>;

  return (
    <Stack spacing={0.25} alignItems={{ xs: "flex-start", sm: "flex-end" }}>
      <Typography variant="overline" color="text.secondary">Confidence Rating</Typography>
      <Stack direction="row" spacing={1} alignItems="baseline">
        <Typography variant="h5">{confidence.toFixed(1)}</Typography>
      </Stack>
    </Stack>
  );
}
