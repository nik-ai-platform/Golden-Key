import { LinearProgress, Stack, Typography } from "@mui/material";

export function LoadingState({ message = "Loading data..." }: { message?: string }) {
  return (
    <Stack spacing={1.2}>
      <Typography variant="body2" color="text.secondary">
        {message}
      </Typography>
      <LinearProgress color="secondary" />
    </Stack>
  );
}
