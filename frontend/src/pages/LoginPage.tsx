import { Alert, Box, Button, Card, CardContent, Link, Stack, TextField, Typography } from "@mui/material";
import { FormEvent, useEffect, useState } from "react";
import { Link as RouterLink, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../hooks/useAuth";
import { ThemeToggleButton } from "../components/ThemeToggleButton";

export function LoginPage() {
  const { isAuthenticated, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isAuthenticated) navigate("/dashboard", { replace: true });
  }, [isAuthenticated, navigate]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await login(email, password);
      const redirectPath = (location.state as { from?: string } | null)?.from ?? "/";
      navigate(redirectPath, { replace: true });
    } catch {
      setError("Login failed. Check credentials and try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Box sx={{ minHeight: "100vh", display: "grid", placeItems: "center", background: (theme) => theme.palette.background.default, p: 2, position: "relative" }}>
      <Box sx={{ position: "absolute", top: 16, right: 16 }}>
        <ThemeToggleButton />
      </Box>
      <Card sx={{ width: "100%", maxWidth: 420 }}>
        <CardContent>
          <Stack spacing={2.5} component="form" onSubmit={onSubmit}>
            <Typography variant="h4">Welcome Back</Typography>
            <Typography color="text.secondary">Sign in to access dashboard, predictions, games, intelligence, and analytics.</Typography>
            {error && <Alert severity="error">{error}</Alert>}
            <TextField label="Email" type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
            <TextField label="Password" type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required />
            <Stack direction="row" justifyContent="space-between" flexWrap="wrap" gap={1}>
              <Link component={RouterLink} to="/forgot-password">Forgot password?</Link>
              <Link component={RouterLink} to="/forgot-email">Forgot email?</Link>
            </Stack>
            <Button type="submit" variant="contained" color="primary" disabled={loading}>
              {loading ? "Signing in..." : "Sign In"}
            </Button>
            <Typography textAlign="center" color="text.secondary">No account? <Link component={RouterLink} to="/register">Create one</Link></Typography>
          </Stack>
        </CardContent>
      </Card>
    </Box>
  );
}
