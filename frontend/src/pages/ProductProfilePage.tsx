import LogoutOutlinedIcon from "@mui/icons-material/LogoutOutlined";
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Divider,
  Stack,
  Typography,
} from "@mui/material";
import { useQuery } from "@tanstack/react-query";

import { ErrorState } from "../components/ErrorState";
import { LoadingState } from "../components/LoadingState";
import { useAuth } from "../hooks/useAuth";
import { getProfile } from "../services/productApi";

export function ProductProfilePage() {
  const { logout } = useAuth();

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
