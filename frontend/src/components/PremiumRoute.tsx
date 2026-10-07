import { Alert, Button, Stack, Typography } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { Link as RouterLink, Outlet } from "react-router-dom";
import type { ReactNode } from "react";
import { useAuth } from "../hooks/useAuth";
import { getSubscription } from "../services/subscriptionService";
import { LoadingState } from "./LoadingState";

export function PremiumRoute({ children, preview }: { children?: ReactNode; preview?: ReactNode }) {
  const { user, isAuthenticated, isBootstrapping } = useAuth();
  const isAdmin = isAuthenticated && user?.role === "admin";
  const query = useQuery({
    queryKey: ["subscriptions", "me"],
    queryFn: getSubscription,
    enabled: isAuthenticated && !isAdmin && !isBootstrapping,
    staleTime: 0,
    retry: false,
  });
  if (isBootstrapping || (!isAdmin && query.isPending && isAuthenticated)) {
    return <LoadingState message="Checking Premium access..." />;
  }
  if (isAdmin || (isAuthenticated && !query.isError && !query.isFetching && query.data?.active === true)) {
    return children ?? <Outlet />;
  }
  if (query.isFetching) return <LoadingState message="Checking Premium access..." />;
  if (query.isError) return (
    <Stack spacing={2}>
      <Alert severity="error">Unable to verify Premium access. Your account and billing remain available.</Alert>
      <Button onClick={() => void query.refetch()}>Refresh access</Button>
      <Button component={RouterLink} to="/profile">Account and billing</Button>
    </Stack>
  );
  return preview ?? (
    <Stack spacing={2}>
      <Typography variant="h4" component="h1">Premium feature</Typography>
      <Typography>Free Preview includes the slate overview and metric education. Picks, odds, analysis, saved picks, parlays and performance require active Premium access.</Typography>
      <Button component={RouterLink} to="/profile" variant="contained">Explore Premium</Button>
      <Button component={RouterLink} to="/dashboard">Free Preview dashboard</Button>
    </Stack>
  );
}
