import { Card, CardContent, Stack, Typography } from "@mui/material";

export function PersonalAIPanel() {
  return (
    <Card>
      <CardContent>
        <Typography variant="h6" gutterBottom>Your Golden Key Profile</Typography>
        <Stack spacing={0.75}>
          <Typography variant="body2">Risk: Moderate</Typography>
          <Typography variant="body2">Best Market: ATS</Typography>
          <Typography variant="body2">Best Sport: NBA</Typography>
          <Typography variant="body2">Your Strength: Underdog Value</Typography>
          <Typography variant="body2">Your Improvement: Totals Analysis</Typography>
        </Stack>
      </CardContent>
    </Card>
  );
}
