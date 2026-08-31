import LogoutOutlinedIcon from "@mui/icons-material/LogoutOutlined";
import {
  Box,
  Alert,
  Button,
  Card,
  CardContent,
  Chip,
  Divider,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { FormEvent, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { useAuth } from "../hooks/useAuth";
import { getProfile } from "../services/productApi";
import { setRecoveryEmail, verifyRecoveryEmail } from "../services/authService";

export function ProductProfilePage() {
  const { logout } = useAuth();
  const [recoveryEmail, setRecoveryEmailValue] = useState("");
  const [verificationCode, setVerificationCode] = useState("");
  const [codeRequested, setCodeRequested] = useState(false);
  const [recoveryMessage, setRecoveryMessage] = useState("");
  const [recoveryError, setRecoveryError] = useState("");
  const [recoveryLoading, setRecoveryLoading] = useState(false);

  const query = useQuery({
    queryKey: ["product", "profile"],
    queryFn: getProfile,
  });

  if (query.isLoading) {
    return <LoadingState message="Loading profile..." />;
  }

  if (query.isError) {
    return (
      <ErrorState
        kind="generic"
        detail="Unable to load profile right now."
        onRetry={() => void query.refetch()}
      />
    );
  }

  const user = query.data!;

  async function requestVerification(event: FormEvent) {
    event.preventDefault();
    setRecoveryLoading(true);
    setRecoveryError("");
    setRecoveryMessage("");
    try {
      const response = await setRecoveryEmail(recoveryEmail);
      setRecoveryMessage(response.message);
      setCodeRequested(true);
      await query.refetch();
    } catch {
      setRecoveryError("Unable to update the recovery email.");
    } finally {
      setRecoveryLoading(false);
    }
  }

  async function confirmVerification(event: FormEvent) {
    event.preventDefault();
    setRecoveryLoading(true);
    setRecoveryError("");
    try {
      const response = await verifyRecoveryEmail(verificationCode);
      setRecoveryMessage(response.message);
      setCodeRequested(false);
      setVerificationCode("");
      await query.refetch();
    } catch {
      setRecoveryError("The verification code is invalid or expired.");
    } finally {
      setRecoveryLoading(false);
    }
  }

  return (
    <Stack spacing={3}>
      <Box>
        <Typography variant="h4" fontWeight={700}>
          Profile
        </Typography>

        <Typography color="text.secondary" sx={{ mt: 1 }}>
          Your Golden Key account and access information.
        </Typography>
      </Box>

      <Card
        variant="outlined"
        sx={{
          maxWidth: 680,
          borderRadius: 3,
        }}
      >
        <CardContent
          sx={{
            p: { xs: 2.5, md: 3 },
            "&:last-child": {
              pb: { xs: 2.5, md: 3 },
            },
          }}
        >
          <Stack spacing={3}>
            <Box>
              <Typography
                variant="overline"
                color="text.secondary"
                fontWeight={700}
              >
                Account
              </Typography>

              <Typography variant="h5" fontWeight={700} sx={{ mt: 0.5 }}>
                {user.username}
              </Typography>
            </Box>

            <Divider />

            <Stack spacing={2.5}>
              <Box>
                <Typography variant="body2" color="text.secondary">
                  Email
                </Typography>

                <Typography fontWeight={600} sx={{ mt: 0.5 }}>
                  {user.email}
                </Typography>
              </Box>

              <Box>
                <Typography variant="body2" color="text.secondary">
                  Access Level
                </Typography>

                <Chip
                  size="small"
                  label={user.premium ? "Premium" : "Standard"}
                  color={user.premium ? "primary" : "default"}
                  sx={{ mt: 1 }}
                />
              </Box>
            </Stack>

            <Divider />

            <Stack spacing={2} component="form" onSubmit={requestVerification}>
              <Box>
                <Typography variant="h6" fontWeight={700}>Account Recovery</Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                  Add a secondary email to recover your sign-in email.
                </Typography>
              </Box>
              {user.recovery_email_masked ? (
                <Stack direction={{ xs: "column", sm: "row" }} spacing={1} alignItems={{ sm: "center" }}>
                  <Typography fontWeight={600}>{user.recovery_email_masked}</Typography>
                  <Chip
                    size="small"
                    label={user.recovery_email_verified ? "Verified" : "Not verified"}
                    color={user.recovery_email_verified ? "success" : "warning"}
                  />
                </Stack>
              ) : (
                <Typography variant="body2" color="text.secondary">No recovery email configured.</Typography>
              )}
              {recoveryMessage ? <Alert severity="success">{recoveryMessage}</Alert> : null}
              {recoveryError ? <Alert severity="error">{recoveryError}</Alert> : null}
              <TextField
                label="Recovery email"
                type="email"
                value={recoveryEmail}
                onChange={(event) => setRecoveryEmailValue(event.target.value)}
                required
              />
              <Button type="submit" variant="contained" disabled={recoveryLoading}>
                {user.recovery_email_masked ? "Update recovery email" : "Add recovery email"}
              </Button>
            </Stack>

            {codeRequested ? (
              <Stack spacing={2} component="form" onSubmit={confirmVerification}>
                <TextField
                  label="Verification code"
                  value={verificationCode}
                  onChange={(event) => setVerificationCode(event.target.value.replace(/\D/g, "").slice(0, 6))}
                  inputProps={{ inputMode: "numeric", pattern: "[0-9]{6}", maxLength: 6 }}
                  required
                />
                <Button type="submit" variant="outlined" disabled={recoveryLoading}>
                  Verify
                </Button>
              </Stack>
            ) : null}

            <Divider />

            <Box>
              <Button
                variant="outlined"
                startIcon={<LogoutOutlinedIcon />}
                onClick={logout}
              >
                Sign Out
              </Button>
            </Box>
          </Stack>
        </CardContent>
      </Card>
    </Stack>
  );
}
