import { Alert, Button, Link, Stack, TextField, Typography } from "@mui/material";
import { FormEvent, useState } from "react";
import { Link as RouterLink } from "react-router-dom";

import { RecoveryLayout } from "../components/RecoveryLayout";
import { forgotEmail, verifyForgotEmail } from "../services/authService";

export function ForgotEmailPage() {
  const [recoveryEmail, setRecoveryEmail] = useState("");
  const [code, setCode] = useState("");
  const [requested, setRequested] = useState(false);
  const [maskedEmail, setMaskedEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function requestCode(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      await forgotEmail(recoveryEmail);
      setRequested(true);
    } catch {
      setError("Account recovery is temporarily unavailable. Please try again later.");
    } finally {
      setLoading(false);
    }
  }

  async function verifyCode(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const result = await verifyForgotEmail({ recovery_email: recoveryEmail, code });
      setMaskedEmail(result.email);
    } catch {
      setError("The recovery code is invalid or expired.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <RecoveryLayout>
      <Stack spacing={2.5} component="form" onSubmit={requested ? verifyCode : requestCode}>
        <Typography variant="h4">{maskedEmail ? "Account found" : "Forgot your email?"}</Typography>
        {maskedEmail ? (
          <>
            <Typography color="text.secondary">Your Golden Key sign-in email:</Typography>
            <Typography variant="h6" fontWeight={700}>{maskedEmail}</Typography>
          </>
        ) : (
          <>
            <Typography color="text.secondary">
              Enter the verified recovery email associated with your Golden Key account.
            </Typography>
            {requested ? (
              <Alert severity="success">
                If a verified recovery account matches that address, a recovery code has been sent.
              </Alert>
            ) : null}
            {error ? <Alert severity="error">{error}</Alert> : null}
            <TextField
              label="Recovery email"
              type="email"
              autoComplete="email"
              value={recoveryEmail}
              onChange={(event) => setRecoveryEmail(event.target.value)}
              disabled={requested}
              required
            />
            {requested ? (
              <TextField
                label="Recovery code"
                value={code}
                onChange={(event) => setCode(event.target.value.replace(/\D/g, "").slice(0, 6))}
                inputProps={{ inputMode: "numeric", pattern: "[0-9]{6}", maxLength: 6 }}
                required
              />
            ) : null}
            <Button type="submit" variant="contained" disabled={loading}>
              {loading ? "Please wait..." : requested ? "Verify code" : "Send recovery code"}
            </Button>
          </>
        )}
        <Link component={RouterLink} to="/login" textAlign="center">Back to sign in</Link>
        <Typography variant="body2" color="text.secondary" textAlign="center">
          Can't access your recovery email?{" "}
          <Link href="mailto:support@nik-ai-platform.com">Contact support.</Link>
        </Typography>
      </Stack>
    </RecoveryLayout>
  );
}