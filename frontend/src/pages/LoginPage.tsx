import { Alert, Box, Button, Card, CardContent, Link, Stack, TextField, Typography } from "@mui/material";
import { FormEvent, useEffect, useState } from "react";
import { Link as RouterLink, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../hooks/useAuth";

export function LoginPage() {
  const { isAuthenticated, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("admin@nik.ai");
  const [password, setPassword] = useState("admin123");
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
    <Box sx={{ minHeight: "100vh", display: "grid", placeItems: "center", background: "radial-gradient(circle at 20% 20%, #ccfbf1 0%, #f8fafc 45%, #fef9c3 100%)", p: 2 }}>
      <Card sx={{ width: "100%", maxWidth: 420 }}>
        <CardContent>
          <Stack spacing={2.5} component="form" onSubmit={onSubmit}>
            <Typography variant="h4">Welcome Back</Typography>
            <Typography color="text.secondary">Sign in to access dashboard, predictions, games, intelligence, and analytics.</Typography>
            {error && <Alert severity="error">{error}</Alert>}
            <TextField label="Email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
            <TextField label="Password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required />
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
