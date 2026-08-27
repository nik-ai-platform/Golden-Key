import ArrowBackOutlinedIcon from "@mui/icons-material/ArrowBackOutlined";
import { Button, Stack, Typography } from "@mui/material";
import { useNavigate } from "react-router-dom";

export function NotFoundPage() {
  const navigate = useNavigate();

  return (
    <Stack alignItems="center" justifyContent="center" spacing={2} sx={{ minHeight: "60vh", textAlign: "center", px: 2 }}>
      <Typography variant="overline" color="text.secondary">Golden Key</Typography>
      <Typography variant="h3">Page not found</Typography>
      <Typography color="text.secondary" sx={{ maxWidth: 480 }}>The page or game you requested does not exist.</Typography>
      <Button variant="contained" startIcon={<ArrowBackOutlinedIcon />} onClick={() => navigate("/dashboard")} sx={{ mt: 2 }}>Return to dashboard</Button>
    </Stack>
  );
}
