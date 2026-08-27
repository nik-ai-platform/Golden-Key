import { Alert, AlertTitle, Button } from "@mui/material";

export default function DashboardError({ reset }: { reset: () => void }) {
  return (
    <Alert severity="error" action={<Button color="inherit" onClick={reset}>Try again</Button>}>
      <AlertTitle>Golden Key could not load today's intelligence.</AlertTitle>
      Check the backend API or try again.
    </Alert>
  );
}
