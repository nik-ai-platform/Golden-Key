import BookmarkBorderOutlinedIcon from "@mui/icons-material/BookmarkBorderOutlined";
import CasinoOutlinedIcon from "@mui/icons-material/CasinoOutlined";
import DashboardOutlinedIcon from "@mui/icons-material/DashboardOutlined";
import DirectionsRunOutlinedIcon from "@mui/icons-material/DirectionsRunOutlined";
import LogoutOutlinedIcon from "@mui/icons-material/LogoutOutlined";
import MenuOutlinedIcon from "@mui/icons-material/MenuOutlined";
import PersonOutlineOutlinedIcon from "@mui/icons-material/PersonOutlineOutlined";
import SportsBasketballOutlinedIcon from "@mui/icons-material/SportsBasketballOutlined";
import TimelineOutlinedIcon from "@mui/icons-material/TimelineOutlined";
import {
  AppBar,
  Box,
  Divider,
  Drawer,
  IconButton,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Stack,
  Toolbar,
  Typography,
} from "@mui/material";
import { useState } from "react";
import { Link as RouterLink, Outlet, useLocation } from "react-router-dom";

import { useAuth } from "../hooks/useAuth";
import { MobileNav } from "../components/MobileNav";
import { ThemeToggleButton } from "../components/ThemeToggleButton";

const drawerWidth = 184;

const navItems = [
  { label: "Dashboard", path: "/dashboard", icon: <DashboardOutlinedIcon />, roles: ["user", "viewer", "analyst", "admin"] },
  { label: "Games", path: "/games", icon: <SportsBasketballOutlinedIcon />, roles: ["user", "viewer", "analyst", "admin"] },
  { label: "Saved Picks", path: "/saved-picks", icon: <BookmarkBorderOutlinedIcon />, roles: ["user", "viewer", "analyst", "admin"] },
  { label: "Parlay Optimizer", path: "/parlays", icon: <CasinoOutlinedIcon />, roles: ["user", "viewer", "analyst", "admin"] },
  { label: "Performance", path: "/performance", icon: <TimelineOutlinedIcon />, roles: ["user", "viewer", "analyst", "admin"] },
  { label: "Profile", path: "/profile", icon: <PersonOutlineOutlinedIcon />, roles: ["user", "viewer", "analyst", "admin"] },
];

export function AppLayout() {
  const location = useLocation();
  const { user, logout } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);

  function navigation() {
    const availableItems = navItems.filter((item) => user && item.roles.includes(user.role));

    return (
      <>
        <Toolbar sx={{ px: 2 }}>
          <Stack direction="row" spacing={1} alignItems="center">
            <DirectionsRunOutlinedIcon color="primary" fontSize="small" />
            <Typography variant="subtitle1" fontWeight={900}>Golden Key</Typography>
          </Stack>
        </Toolbar>
        <Divider />
        <List sx={{ px: 1, py: 1.5 }}>
          {availableItems.map((item) => (
            <ListItemButton
              key={item.path}
              component={RouterLink}
              to={item.path}
              selected={location.pathname === item.path || location.pathname.startsWith(`${item.path}/`)}
              aria-current={location.pathname === item.path || location.pathname.startsWith(`${item.path}/`) ? "page" : undefined}
              onClick={() => setMobileOpen(false)}
              sx={{
                minHeight: 38,
                px: 1.25,
                py: 0.5,
                mb: 0.5,
                borderRadius: "var(--gk-radius-sm)",
                color: "var(--gk-text-secondary)",
                borderLeft: "2px solid transparent",
                "&.Mui-selected": {
                  color: "var(--gk-gold-bright)",
                  backgroundColor: "var(--gk-gold-soft)",
                  borderLeftColor: "var(--gk-gold)",
                },
              }}
            >
              <ListItemIcon sx={{ color: "inherit", minWidth: 32, "& .MuiSvgIcon-root": { fontSize: 19 } }}>{item.icon}</ListItemIcon>
              <ListItemText primary={item.label} primaryTypographyProps={{ variant: "body2", fontWeight: 750 }} />
            </ListItemButton>
          ))}
        </List>
      </>
    );
  }

  return (
    <Box sx={{ display: "flex", minHeight: "100vh", backgroundColor: "background.default" }}>
      <AppBar
        position="fixed"
        color="inherit"
        elevation={0}
        sx={{
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          ml: { sm: `${drawerWidth}px` },
          borderBottom: "1px solid",
          borderBottomColor: "divider",
          backgroundColor: "rgba(9, 11, 15, 0.96)",
          color: "var(--gk-text)",
          backdropFilter: "blur(12px)",
        }}
      >
        <Toolbar sx={{ minHeight: "56px !important", px: { xs: 1.5, sm: 2.25 }, justifyContent: "space-between" }}>
          <Stack direction="row" spacing={1.2} alignItems="center">
            <IconButton aria-label="Open navigation" sx={{ display: { sm: "none" } }} onClick={() => setMobileOpen((value) => !value)} color="primary">
              <MenuOutlinedIcon />
            </IconButton>
            <Stack>
              <Typography variant="subtitle1" fontWeight={850}>Sports Intelligence</Typography>
              <Typography variant="caption" color="text.secondary">Daily model intelligence · {user?.role ?? "user"}</Typography>
            </Stack>
          </Stack>
          <Stack direction="row" spacing={0.5} alignItems="center">
            <ThemeToggleButton />
            <IconButton aria-label="Sign Out" onClick={logout} color="primary">
              <LogoutOutlinedIcon />
            </IconButton>
          </Stack>
        </Toolbar>
      </AppBar>

      <Drawer
        variant="temporary"
        open={mobileOpen}
        onClose={() => setMobileOpen(false)}
        sx={{
          display: { xs: "block", sm: "none" },
          [`& .MuiDrawer-paper`]: {
            width: drawerWidth,
            boxSizing: "border-box",
            backgroundColor: "#0b0d11",
            color: "var(--gk-text)",
          },
        }}
      >
        {navigation()}
      </Drawer>

      <Drawer
        variant="permanent"
        sx={{
          display: { xs: "none", sm: "block" },
          width: drawerWidth,
          flexShrink: 0,
          [`& .MuiDrawer-paper`]: {
            width: drawerWidth,
            boxSizing: "border-box",
            borderRight: "1px solid",
            borderRightColor: "rgba(214, 173, 69, 0.18)",
            backgroundColor: "#0b0d11",
            color: "var(--gk-text)",
          },
        }}
      >
        {navigation()}
      </Drawer>

      <Box component="main" sx={{ flexGrow: 1, minWidth: 0, p: { xs: 2, sm: 2.25 }, pb: { xs: 11, sm: 2.25 }, mt: 7 }}>
        <Outlet />
        <Box component="footer" sx={{ mt: 2.5, pt: 1.5, borderTop: "1px solid", borderTopColor: "divider" }}>
          <Typography variant="caption" color="text.secondary">
            Golden Key Sports Intelligence
          </Typography>
        </Box>
      </Box>
      <MobileNav />
    </Box>
  );
}
