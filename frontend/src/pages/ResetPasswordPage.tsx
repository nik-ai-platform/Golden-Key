import { Alert, Button, Link, Stack, TextField, Typography } from "@mui/material";
import { FormEvent, useState } from "react";
import { Link as RouterLink, useSearchParams } from "react-router-dom";

import { RecoveryLayout } from "../components/RecoveryLayout";
import { resetPassword } from "../services/authService";

export function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") ?? "";
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setError("");
    if (!token) {
      setError("This password reset link is invalid or has expired.");
      return;
    }
    if (password !== confirmation) {
      setError("Passwords must match.");
      return;
    }

    setLoading(true);
    try {
      await resetPassword({ token, new_password: password });
      setSuccess(true);
    } catch {
      setError("This password reset link is invalid or has expired.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <RecoveryLayout>
      {success ? (
        <Stack spacing={2.5}>
          <Typography variant="h4">Password updated</Typography>
          <Alert severity="success">Your password has been reset successfully.</Alert>
          <Button component={RouterLink} to="/login" variant="contained">Continue to Login</Button>
        </Stack>
      ) : (
        <Stack spacing={2.5} component="form" onSubmit={onSubmit}>
          <Typography variant="h4">Choose a new password</Typography>
          <Typography color="text.secondary">Use at least 8 characters.</Typography>
          {error ? <Alert severity="error">{error}</Alert> : null}
          <TextField
            label="New password"
            type="password"
            autoComplete="new-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            inputProps={{ minLength: 8, maxLength: 256 }}
            required
          />
          <TextField
            label="Confirm password"
            type="password"
            autoComplete="new-password"
            value={confirmation}
            onChange={(event) => setConfirmation(event.target.value)}
            inputProps={{ minLength: 8, maxLength: 256 }}
            required
          />
          <Button type="submit" variant="contained" disabled={loading}>
            {loading ? "Updating..." : "Update password"}
          </Button>
          <Link component={RouterLink} to="/login" textAlign="center">Back to Login</Link>
        </Stack>
      )}
    </RecoveryLayout>
  );
}