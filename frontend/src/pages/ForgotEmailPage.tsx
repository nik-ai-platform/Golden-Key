import { Button, Link, Stack, Typography } from "@mui/material";
import { Link as RouterLink } from "react-router-dom";

import { RecoveryLayout } from "../components/RecoveryLayout";

export function ForgotEmailPage() {
  return (
    <RecoveryLayout>
      <Stack spacing={2.5}>
        <Typography variant="h4">Recover your account</Typography>
        <Typography color="text.secondary">
          If you no longer remember the email associated with your Golden Key account,
          contact support for account recovery.
        </Typography>
        <Button
          component="a"
          href="mailto:support@nik-ai-platform.com"
          variant="contained"
        >
          Contact support
        </Button>
        <Link component={RouterLink} to="/login" textAlign="center">Back to Login</Link>
      </Stack>
    </RecoveryLayout>
  );
}