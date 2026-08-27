import { Alert, Box } from "@mui/material";
import { Navigate, Outlet } from "react-router-dom";

import { useAuth } from "../hooks/useAuth";
import type { AuthUser } from "../types/auth";

type RoleRouteProps = {
  allowedRoles: AuthUser["role"][];
};

export function RoleRoute({ allowedRoles }: RoleRouteProps) {
  const { user } = useAuth();

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (!allowedRoles.includes(user.role)) {
    return (
      <Box sx={{ p: 2 }}>
        <Alert severity="error">Insufficient permissions</Alert>
      </Box>
    );
  }

  return <Outlet />;
}
