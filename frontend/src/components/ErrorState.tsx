import { Alert, Button, Stack, Typography } from "@mui/material";

type ErrorKind = "unauthorized" | "server" | "timeout" | "network" | "generic";

function labelFor(kind: ErrorKind) {
  if (kind === "unauthorized") {
    return "Unauthorized";
  }
  if (kind === "server") {
    return "Server unavailable";
  }
  if (kind === "timeout") {
    return "Network timeout";
  }
  if (kind === "network") {
    return "Network error";
  }
  return "Request failed";
}

export function ErrorState({
  kind,
  detail,
  onRetry,
}: {
  kind: ErrorKind;
  detail?: string;
  onRetry?: () => void;
}) {
  return (
    <Stack spacing={1.5}>
      <Alert severity="error">{labelFor(kind)}</Alert>
      {detail && (
        <Typography variant="body2" color="text.secondary">
          {detail}
        </Typography>
      )}
      {onRetry && (
        <Button variant="outlined" onClick={onRetry} sx={{ width: "fit-content" }}>
          Retry
        </Button>
      )}
    </Stack>
  );
}
