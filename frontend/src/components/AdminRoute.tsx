import { Alert } from "@mui/material";
import { Outlet } from "react-router-dom";

import { useAuth } from "../hooks/useAuth";

export function AdminRoute() {
  const { user } = useAuth();
  if (user?.role !== "admin") {
    return (
      <Alert severity="error" role="alert">
        Administrator access required.
      </Alert>
    );
  }
  return <Outlet />;
}
