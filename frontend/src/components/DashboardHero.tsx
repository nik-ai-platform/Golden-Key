import ArrowForwardRoundedIcon from "@mui/icons-material/ArrowForwardRounded";
import { Box, Button, Stack, Typography } from "@mui/material";

export function DashboardHero() {
  return (
    <Box
      component="section"
      data-testid="dashboard-hero"
      aria-labelledby="dashboard-hero-heading"
      sx={{
        display: "grid",
        gridTemplateColumns: { xs: "minmax(0, 1fr)", md: "minmax(0, 1.1fr) minmax(300px, 0.9fr)" },
        border: "1px solid var(--gk-border-strong)",
        borderRadius: "var(--gk-radius-lg)",
        overflow: "hidden",
        backgroundColor: "var(--gk-surface)",
        boxShadow: "var(--gk-shadow-sm)",
      }}
    >
      <Stack spacing={2} sx={{ p: { xs: 2.5, sm: 3, md: 4 }, alignItems: "flex-start", justifyContent: "center" }}>
        <Typography className="gk-editorial" sx={{ fontSize: "1.4rem", fontWeight: 650 }}>
          Bear A Hand Sports
        </Typography>
        <Typography component="h1" id="dashboard-hero-heading" aria-label="THE GAME. THE DATA. YOUR EDGE." sx={{ fontSize: { xs: "2.6rem", sm: "3.4rem", lg: "4.2rem" }, fontWeight: 850, lineHeight: 1.05, letterSpacing: "-0.045em" }}>
          THE GAME.<br />THE DATA.<br /><Box component="span" sx={{ color: "primary.main" }}>YOUR EDGE.</Box>
        </Typography>
        <Typography color="text.secondary" sx={{ maxWidth: 470, lineHeight: 1.7 }}>
          A clearer view of the slate. Compare market-specific picks, understand the model, and track every outcome.
        </Typography>
        <Button
          component="a"
          href="#upcoming-games-heading"
          endIcon={<ArrowForwardRoundedIcon />}
          sx={{ backgroundColor: "#a4ef18", color: "#060d14", px: 2.5, minHeight: 44, "&:hover": { backgroundColor: "#b6fa39" } }}
        >
          Explore picks
        </Button>
      </Stack>
      <Box
        sx={{
          backgroundColor: "#060d14",
          minWidth: 0,
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          p: { xs: 1, sm: 1.5 },
        }}
      >
        <Box
          component="img"
          src="/Bear_A_Hand_Sports_FullColor.jpg"
          alt="Complete Bear A Hand Sports artwork with bear, globe, charts, wordmark, and decorative odds and percentages that are not live model metrics."
          sx={{
            display: "block",
            width: "100%",
            height: "auto",
            maxHeight: { md: 520 },
            objectFit: "contain",
          }}
        />
      </Box>
    </Box>
  );
}
