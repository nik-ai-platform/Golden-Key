import LogoutOutlinedIcon from "@mui/icons-material/LogoutOutlined";
import { Button, Card, CardContent, Chip, Stack, Typography } from "@mui/material";
import { useQuery } from "@tanstack/react-query";

import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { useAuth } from "../hooks/useAuth";
import { getProfile } from "../services/productApi";

export function ProductProfilePage() {
  const { logout } = useAuth();
  const query = useQuery({ queryKey: ["product", "profile"], queryFn: getProfile });

  if (query.isLoading) return <LoadingState message="Loading profile..." />;
  if (query.isError) return <ErrorState kind="generic" detail="Unable to load profile." onRetry={() => void query.refetch()} />;

  const user = query.data!;
  return (
    <Stack spacing={3}>
      <Typography variant="h4">Profile</Typography>
      <Card variant="outlined" sx={{ maxWidth: 600 }}><CardContent sx={{ p: 3 }}><Stack spacing={3}>
        <Stack spacing={0.5}><Typography variant="overline" color="text.secondary">Username</Typography><Typography variant="h5">{user.username}</Typography></Stack>
        <Stack spacing={0.5}><Typography variant="overline" color="text.secondary">Email</Typography><Typography>{user.email}</Typography></Stack>
        <Stack spacing={0.75} alignItems="flex-start"><Typography variant="overline" color="text.secondary">Membership</Typography><Chip label={user.premium ? "Premium" : "Free"} color={user.premium ? "primary" : "default"} /></Stack>
        <Button variant="outlined" startIcon={<LogoutOutlinedIcon />} onClick={logout} sx={{ alignSelf: "flex-start" }}>Sign out</Button>
      </Stack></CardContent></Card>
    </Stack>
  );
}
