import { Box, Typography } from "@mui/material";

export function ContextPanel() {
  return (
    <Box sx={{ p: 2, borderRadius: 2, backgroundColor: "#ecfeff", border: "1px solid #a7f3d0" }}>
      <Typography variant="subtitle2" gutterBottom>Live context</Typography>
      <Typography variant="body2">Risk: Moderate</Typography>
      <Typography variant="body2">Bankroll: $5,000</Typography>
      <Typography variant="body2">Favorite Team: Atlanta Hawks</Typography>
    </Box>
  );
}
