import { Box, Typography } from "@mui/material";

export function ConfidenceDisplay({ value = 82 }: { value?: number }) {
  return (
    <Box sx={{ display: "inline-flex", alignItems: "center", gap: 1, backgroundColor: "#fef3c7", px: 1.5, py: 0.75, borderRadius: 999 }}>
      <Typography variant="caption" fontWeight={700}>Confidence</Typography>
      <Typography variant="body2" fontWeight={700}>{value}%</Typography>
    </Box>
  );
}
