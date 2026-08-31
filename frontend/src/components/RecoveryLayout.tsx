import { Box, Card, CardContent } from "@mui/material";
import type { ReactNode } from "react";

import { ThemeToggleButton } from "./ThemeToggleButton";

type RecoveryLayoutProps = {
  children: ReactNode;
};

export function RecoveryLayout({ children }: RecoveryLayoutProps) {
  return (
    <Box
      sx={{
        minHeight: "100vh",
        display: "grid",
        placeItems: "center",
        bgcolor: "background.default",
        px: 2,
        py: 6,
        position: "relative",
      }}
    >
      <Box sx={{ position: "absolute", top: 16, right: 16 }}>
        <ThemeToggleButton />
      </Box>
      <Card sx={{ width: "100%", maxWidth: 440 }}>
        <CardContent sx={{ p: { xs: 3, sm: 4 } }}>{children}</CardContent>
      </Card>
    </Box>
  );
}