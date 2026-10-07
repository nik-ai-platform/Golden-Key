import { Alert, Button, Stack, TextField, Typography } from "@mui/material";
import { FormEvent, useState } from "react";
import { confirmEmailVerification, requestEmailVerification } from "../services/authService";

export function EmailVerificationSection({ email, onConfirmed }: { email: string; onConfirmed: () => void }) {
  const [token, setToken] = useState("");
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  async function resend() {
    setPending(true); setError(""); setMessage("");
    try {
      await requestEmailVerification(email);
      setMessage("If this address is eligible, verification instructions will be sent. Check your inbox.");
    } catch { setError("Verification is temporarily unavailable. Please try again."); }
    finally { setPending(false); }
  }
  async function confirm(event: FormEvent) {
    event.preventDefault(); setPending(true); setError(""); setMessage("");
    try {
      await confirmEmailVerification(token);
      setToken(""); setMessage("Email verification confirmed."); onConfirmed();
    } catch { setError("Verification could not be confirmed. The token may be invalid or expired."); }
    finally { setPending(false); }
  }
  return <Stack spacing={2}>
    <Typography component="h2" variant="h6">Sign-in email verification</Typography>
    <Typography variant="body2">Verify your current sign-in address. This does not change your sign-in email.</Typography>
    {message ? <Alert severity="info">{message}</Alert> : null}
    {error ? <Alert severity="error">{error}</Alert> : null}
    <Button onClick={() => void resend()} disabled={pending}>Resend email verification</Button>
    <Stack component="form" onSubmit={confirm} spacing={2}>
      <TextField label="Email verification token" value={token} onChange={(event) => setToken(event.target.value)} required autoComplete="off" />
      <Button type="submit" disabled={pending}>Confirm email verification</Button>
    </Stack>
  </Stack>;
}
