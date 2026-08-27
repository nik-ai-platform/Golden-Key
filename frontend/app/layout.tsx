import React, { useMemo, useState } from "react";
import {
  AppBar,
  Avatar,
  Badge,
  Box,
  Button,
  CssBaseline,
  IconButton,
  Menu,
  MenuItem,
  Stack,
  ThemeProvider,
  Toolbar,
  Tooltip,
  Typography,
  createTheme,
} from "@mui/material";
import NotificationsOutlinedIcon from "@mui/icons-material/NotificationsOutlined";
import LightModeOutlinedIcon from "@mui/icons-material/LightModeOutlined";
import DarkModeOutlinedIcon from "@mui/icons-material/DarkModeOutlined";

import NotificationCenter from "../components/NotificationCenter";
import { getToken } from "../services/session";

type RootLayoutProps = { children: React.ReactNode };

const navigation = [
  { label: "Dashboard", href: "/dashboard" },
  { label: "Games", href: "/games" },
  { label: "Intelligence", href: "/sports-brain" },
  { label: "Portfolio", href: "/portfolio" },
  { label: "Research", href: "/research" },
  { label: "Settings", href: "/settings" },
];

export default function RootLayout({ children }: RootLayoutProps) {
  const [mode, setMode] = useState<"light" | "dark">("light");
  const [userMenuAnchor, setUserMenuAnchor] = useState<null | HTMLElement>(null);
  const [showNotifications, setShowNotifications] = useState(false);

  const isAuthenticated = typeof window !== "undefined" && Boolean(getToken());

  const theme = useMemo(
    () =>
      createTheme({
        palette: {
          mode,
          primary: { main: "#006d5b" },
          secondary: { main: "#b45309" },
          background:
            mode === "light"
              ? { default: "#f4f8f7", paper: "#ffffff" }
              : { default: "#0d1715", paper: "#13211e" },
        },
      }),
    [mode],
  );

  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box sx={{ minHeight: "100vh", bgcolor: "background.default" }}>
        <AppBar position="sticky" color="inherit" elevation={0} sx={{ borderBottom: "1px solid", borderColor: "divider" }}>
          <Toolbar sx={{ gap: 2, alignItems: "center", flexWrap: "wrap" }}>
            <Typography variant="h6" sx={{ fontWeight: 800, mr: 1 }}>Golden Key</Typography>
            <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap", flexGrow: 1 }}>
              {navigation.map((item) => (
                <Button key={item.href} href={item.href} color="inherit" size="small">
                  {item.label}
                </Button>
              ))}
            </Stack>
            <Tooltip title="Notifications">
              <IconButton onClick={() => setShowNotifications((value) => !value)} color="inherit">
                <Badge color="error" variant="dot">
                  <NotificationsOutlinedIcon />
                </Badge>
              </IconButton>
            </Tooltip>
            <Tooltip title="Theme">
              <IconButton onClick={() => setMode((value) => (value === "light" ? "dark" : "light"))} color="inherit">
                {mode === "light" ? <DarkModeOutlinedIcon /> : <LightModeOutlinedIcon />}
              </IconButton>
            </Tooltip>
            <Button onClick={(event) => setUserMenuAnchor(event.currentTarget)} color="inherit" startIcon={<Avatar sx={{ width: 24, height: 24 }}>GK</Avatar>}>
              {isAuthenticated ? "Signed In" : "Guest"}
            </Button>
            <Menu anchorEl={userMenuAnchor} open={Boolean(userMenuAnchor)} onClose={() => setUserMenuAnchor(null)}>
              <MenuItem onClick={() => setUserMenuAnchor(null)}>Profile</MenuItem>
              <MenuItem onClick={() => setUserMenuAnchor(null)}>Account</MenuItem>
              <MenuItem onClick={() => setUserMenuAnchor(null)}>{isAuthenticated ? "Logout" : "Login"}</MenuItem>
            </Menu>
          </Toolbar>
        </AppBar>

        {showNotifications ? (
          <Box sx={{ px: { xs: 2, md: 3 }, pt: 2 }}>
            <NotificationCenter />
          </Box>
        ) : null}

        <Box component="main" sx={{ px: { xs: 2, md: 3 }, py: 3 }}>
          {children}
        </Box>
      </Box>
    </ThemeProvider>
  );
}
