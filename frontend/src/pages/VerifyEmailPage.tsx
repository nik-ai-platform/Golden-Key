import { Alert, Button, Link, Stack, TextField, Typography } from "@mui/material";
import { FormEvent, useState } from "react";
import { Link as RouterLink, useSearchParams } from "react-router-dom";
import { RecoveryLayout } from "../components/RecoveryLayout";
import { confirmEmailVerification } from "../services/authService";

export function VerifyEmailPage() {
  const [params, setParams] = useSearchParams();
  const [token, setToken] = useState(params.get("token") ?? "");
  const [pending, setPending] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [error, setError] = useState("");
  async function submit(event: FormEvent) {
    event.preventDefault(); setPending(true); setError("");
    try {
      await confirmEmailVerification(token);
      setConfirmed(true); setToken(""); setParams({}, { replace: true });
    } catch { setError("Unable to verify this email. The token may be invalid or expired. Sign in to request another verification email."); }
    finally { setPending(false); }
  }
  return <RecoveryLayout><Stack spacing={2.5}>
    <Typography component="h1" variant="h4">Verify your email</Typography>
    {confirmed ? <Alert severity="success">Email verification confirmed. You can sign in to your account.</Alert> : <Stack component="form" spacing={2} onSubmit={submit}>
      <Typography>Confirm the token from your verification email. Opening this page alone does not change your account.</Typography>
      {error ? <Alert severity="error">{error}</Alert> : null}
      <TextField label="Email verification token" value={token} onChange={(event) => setToken(event.target.value)} required autoComplete="off" />
      <Button type="submit" variant="contained" disabled={pending}>{pending ? "Confirming..." : "Confirm email verification"}</Button>
    </Stack>}
    <Link component={RouterLink} to="/login">Back to sign in</Link>
  </Stack></RecoveryLayout>;
}
