import { Box, Button, Stack, Typography } from "@mui/material";
import { Link as RouterLink, Outlet } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { CustomerLinks } from "../components/CustomerLinks";
import { ThemeToggleButton } from "../components/ThemeToggleButton";
import { AppLayout } from "./AppLayout";

export function PublicLayout() {
  const { isAuthenticated } = useAuth();
  if (isAuthenticated) return <AppLayout />;
  return <Box sx={{ maxWidth: 1120, mx: "auto", p: { xs: 2, sm: 3 } }}>
    <Stack component="header" spacing={2} sx={{ mb: 4 }}>
      <Typography className="gk-editorial" variant="h5">Bear A Hand Sports</Typography>
      <Stack direction="row" useFlexGap flexWrap="wrap" spacing={1}>
        <Button component={RouterLink} to="/">Product</Button>
        <Button component={RouterLink} to="/how-it-works">How It Works</Button>
        <Button component={RouterLink} to="/login">Sign in</Button>
        <Button component={RouterLink} to="/register" variant="contained">Join Free Preview</Button>
        <ThemeToggleButton />
      </Stack>
    </Stack>
    <Box component="main"><Outlet /></Box>
    <Box component="footer" sx={{ mt: 4, pt: 2, borderTop: 1, borderColor: "divider" }}><CustomerLinks /></Box>
  </Box>;
}
