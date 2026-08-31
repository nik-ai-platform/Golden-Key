import { Alert, Button, Link, Stack, TextField, Typography } from "@mui/material";
import { FormEvent, useState } from "react";
import { Link as RouterLink } from "react-router-dom";

import { RecoveryLayout } from "../components/RecoveryLayout";
import { forgotPassword } from "../services/authService";

const confirmation = "If an account exists for that email, password reset instructions have been sent.";

export function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      await forgotPassword(email);
      setSubmitted(true);
    } catch {
      setError("Recovery is temporarily unavailable. Please try again later.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <RecoveryLayout>
      <Stack spacing={2.5} component="form" onSubmit={onSubmit}>
        <Typography variant="h4">Reset your password</Typography>
        <Typography color="text.secondary">
          Enter the email used for your Golden Key account.
        </Typography>
        {submitted ? <Alert severity="success">{confirmation}</Alert> : null}
        {error ? <Alert severity="error">{error}</Alert> : null}
        {!submitted ? (
          <>
            <TextField
              label="Email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />
            <Button type="submit" variant="contained" disabled={loading}>
              {loading ? "Sending..." : "Send reset instructions"}
            </Button>
          </>
        ) : null}
        <Link component={RouterLink} to="/login" textAlign="center">Back to Login</Link>
      </Stack>
    </RecoveryLayout>
  );
}