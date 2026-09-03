import { Alert, Box, Button, Card, CardContent, Link, Stack, TextField, Typography } from "@mui/material";
import { FormEvent, useEffect, useState } from "react";
import { Link as RouterLink, useNavigate } from "react-router-dom";

import { register } from "../services/authService";
import { useAuth } from "../hooks/useAuth";

type ApiRequestError = {
  status?: number;
  message?: string;
};

function getRegistrationErrorMessage(error: unknown): string {
  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }

  if (
    typeof error === "object" &&
    error !== null &&
    "message" in error &&
    typeof (error as ApiRequestError).message === "string"
  ) {
    const message = (error as ApiRequestError).message?.trim();

    if (message) {
      return message;
    }
  }

  return "Registration failed. Please try again.";
}

export function RegisterPage() {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isAuthenticated) navigate("/dashboard", { replace: true });
  }, [isAuthenticated, navigate]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    setLoading(true);
    try {
      await register({ username, email, password });
      navigate("/login", { replace: true });
    } catch (caught: unknown) {
      setError(getRegistrationErrorMessage(caught));
    } finally {
      setLoading(false);
    }
  }

  return (
    <Box sx={{ minHeight: "100vh", display: "grid", placeItems: "center", background: "radial-gradient(circle at 20% 20%, #ccfbf1 0%, #f8fafc 45%, #fef9c3 100%)", p: 2 }}>
      <Card sx={{ width: "100%", maxWidth: 440 }}>
        <CardContent sx={{ p: 4 }}>
          <Stack spacing={2.5} component="form" onSubmit={onSubmit}>
            <Box><Typography variant="overline" color="text.secondary">Golden Key</Typography><Typography variant="h4">Create account</Typography><Typography color="text.secondary" sx={{ mt: 1 }}>Start tracking predictions and performance.</Typography></Box>
            {error ? <Alert severity="error">{error}</Alert> : null}
            <TextField label="Username" value={username} onChange={(event) => setUsername(event.target.value)} required />
            <TextField label="Email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
            <TextField label="Password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} inputProps={{ minLength: 8 }} required />
            <Button type="submit" variant="contained" disabled={loading}>{loading ? "Creating account..." : "Create account"}</Button>
            <Typography textAlign="center" color="text.secondary">Already registered? <Link component={RouterLink} to="/login">Sign in</Link></Typography>
          </Stack>
        </CardContent>
      </Card>
    </Box>
  );
}
