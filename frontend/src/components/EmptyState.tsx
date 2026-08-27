import { Paper, Stack, Typography } from "@mui/material";

export function EmptyState({ title = "No data available", description }: { title?: string; description?: string }) {
  return (
    <Paper variant="outlined" sx={{ p: { xs: 4, md: 6 }, borderStyle: "dashed", textAlign: "center", borderRadius: 2 }}>
      <Stack spacing={1} alignItems="center">
        <Typography variant="h6">{title}</Typography>
        {description && (
          <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 560, lineHeight: 1.7 }}>
            {description}
          </Typography>
        )}
      </Stack>
    </Paper>
  );
}
