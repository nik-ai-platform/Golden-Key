import { Box, Stack, Typography } from "@mui/material";

export function DashboardHero({ predictionCount }: { predictionCount: number }) {
  const dateLabel = new Date().toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" });

  return (
    <Box
      component="section"
      data-testid="dashboard-hero"
      sx={{
        position: "relative",
        overflow: "hidden",
        border: "1px solid var(--gk-border-strong)",
        borderRadius: "var(--gk-radius-lg)",
        p: { xs: 2, sm: 3.5, md: 4.5 },
        backgroundColor: "var(--gk-surface-raised)",
        boxShadow: "var(--gk-shadow-sm)",
        "&::before": {
          content: '""',
          position: "absolute",
          inset: "0 auto 0 0",
          width: 3,
          backgroundColor: "var(--gk-gold)",
        },
      }}
    >
      <Typography variant="overline" color="primary.main" fontWeight={800}>Bear A Hand Intelligence</Typography>
      <Stack direction={{ xs: "column", md: "row" }} justifyContent="space-between" alignItems={{ md: "flex-end" }} spacing={{ xs: 2, md: 5 }} sx={{ mt: { xs: 1, sm: 1.5 } }}>
        <Box sx={{ minWidth: 0 }}>
          <Typography className="gk-editorial" variant="h3" sx={{ color: "var(--gk-text)", fontSize: { xs: "2.5rem", sm: "3rem" }, fontWeight: 600, lineHeight: 1.04, letterSpacing: 0 }}>
            Today&apos;s edge
          </Typography>
          <Typography color="text.secondary" sx={{ mt: 1.25, maxWidth: 660, lineHeight: 1.7 }}>
            Production-model opportunities informed by NPI, Confidence Rating, Model Probability, and market-specific edge.
          </Typography>
        </Box>
        <Stack alignItems={{ xs: "flex-start", md: "flex-end" }} spacing={0.75} sx={{ flexShrink: 0 }}>
          <Typography color="text.secondary">{dateLabel}</Typography>
          <Typography className="gk-data" data-testid="active-prediction-count" color="info.main" fontWeight={700}>
            {predictionCount} active predictions
          </Typography>
        </Stack>
      </Stack>
    </Box>
  );
}
