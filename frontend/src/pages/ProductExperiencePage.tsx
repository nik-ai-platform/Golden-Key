import { Box, Button, Card, CardContent, Grid2 as Grid, Stack, Typography } from "@mui/material";
import { Link as RouterLink } from "react-router-dom";

import DashboardPage from "../../app/dashboard/page";
import LivePage from "../../app/live/page";
import SettingsPage from "../../app/settings/page";

export function ProductExperiencePage() {
  return (
    <Stack spacing={3}>
      <Box>
        <Typography variant="h4" gutterBottom>
          Product Experience Preview
        </Typography>
        <Typography color="text.secondary">
          The new product shell now lives inside the existing control-room layout so it feels like a first-class experience rather than a detached scaffold.
        </Typography>
      </Box>

      <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
        <Button component={RouterLink} to="/dashboard" variant="contained">
          Return to main dashboard
        </Button>
        <Button component={RouterLink} to="/product/live" variant="outlined">
          Open live preview
        </Button>
        <Button component={RouterLink} to="/product/settings" variant="outlined">
          Open settings preview
        </Button>
      </Stack>

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, lg: 6 }}>
          <Card sx={{ height: "100%", background: "linear-gradient(135deg, #ecfeff 0%, #f8fafc 100%)" }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Experience shell
              </Typography>
              <DashboardPage />
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, lg: 6 }}>
          <Card sx={{ height: "100%" }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Live intelligence
              </Typography>
              <LivePage />
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Preferences and controls
              </Typography>
              <SettingsPage />
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Stack>
  );
}
