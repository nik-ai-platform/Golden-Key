import { Box, Chip, LinearProgress, Stack, Typography } from "@mui/material";

export interface NPIScoreProps {
  score: number;
}

export function NPIScore({ score }: NPIScoreProps) {
  const label = score >= 160 ? "Elite" : score >= 130 ? "Strong" : score >= 100 ? "Moderate" : "Low";
  const percentage = Math.min(Math.max((score / 200) * 100, 0), 100);

  return (
    <Box>
      <Stack direction="row" alignItems="flex-end" justifyContent="space-between">
        <Box>
          <Typography variant="overline" color="text.secondary" sx={{ letterSpacing: 1.2 }}>Nik Power Index</Typography>
          <Typography variant="h4">
            {score.toFixed(1)}
            <Typography component="span" variant="body2" color="text.secondary" sx={{ ml: 0.75 }}>
              / 200
            </Typography>
          </Typography>
        </Box>
        <Chip label={label} size="small" variant="outlined" />
      </Stack>
      <LinearProgress
        variant="determinate"
        value={percentage}
        aria-label={`NPI score ${score.toFixed(1)} out of 200`}
        sx={{ mt: 1.5, height: 10, borderRadius: 1 }}
      />
    </Box>
  );
}
