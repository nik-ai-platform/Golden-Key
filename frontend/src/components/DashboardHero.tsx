import { Box, Stack, Typography } from "@mui/material";

export function DashboardHero({ predictionCount }: { predictionCount: number }) {
  const dateLabel = new Date().toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" });

  return (
    <Box component="section" sx={{ border: "1px solid", borderColor: "divider", borderRadius: 2, p: { xs: 3, md: 5 }, background: "linear-gradient(135deg, rgba(15,118,110,0.12), rgba(255,255,255,0.72) 55%, rgba(250,204,21,0.12))" }}>
      <Typography variant="overline" color="primary.main" fontWeight={700}>Golden Key Intelligence</Typography>
      <Stack direction={{ xs: "column", md: "row" }} justifyContent="space-between" alignItems={{ md: "flex-end" }} spacing={3} sx={{ mt: 2 }}>
        <Box>
          <Typography variant="h3">Today's edge</Typography>
          <Typography color="text.secondary" sx={{ mt: 1.5, maxWidth: 680, lineHeight: 1.7 }}>Production-model opportunities ranked by confidence, NPI strength, and simulated edge.</Typography>
        </Box>
        <Stack alignItems={{ xs: "flex-start", md: "flex-end" }} spacing={0.5}>
          <Typography>{dateLabel}</Typography>
          <Typography variant="overline" color="text.secondary">{predictionCount} active predictions</Typography>
        </Stack>
      </Stack>
    </Box>
  );
}
