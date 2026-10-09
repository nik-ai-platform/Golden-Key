import BookmarkBorderOutlinedIcon from "@mui/icons-material/BookmarkBorderOutlined";
import CasinoOutlinedIcon from "@mui/icons-material/CasinoOutlined";
import DashboardOutlinedIcon from "@mui/icons-material/DashboardOutlined";
import DirectionsRunOutlinedIcon from "@mui/icons-material/DirectionsRunOutlined";
import LogoutOutlinedIcon from "@mui/icons-material/LogoutOutlined";
import MenuOutlinedIcon from "@mui/icons-material/MenuOutlined";
import HelpOutlineOutlinedIcon from "@mui/icons-material/HelpOutlineOutlined";
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
import { CustomerLinks } from "../components/CustomerLinks";

const drawerWidth = 208;

const navItems = [
  { label: "Dashboard", path: "/dashboard", icon: <DashboardOutlinedIcon />, roles: ["user", "viewer", "analyst", "admin"] },
  { label: "Games", path: "/games", icon: <SportsBasketballOutlinedIcon />, roles: ["user", "viewer", "analyst", "admin"] },
  { label: "Saved Picks", path: "/saved-picks", icon: <BookmarkBorderOutlinedIcon />, roles: ["user", "viewer", "analyst", "admin"] },
  { label: "Parlay Optimizer", path: "/parlays", icon: <CasinoOutlinedIcon />, roles: ["user", "viewer", "analyst", "admin"] },
  { label: "Performance", path: "/performance", icon: <TimelineOutlinedIcon />, roles: ["user", "viewer", "analyst", "admin"] },
  { label: "Profile", path: "/profile", icon: <PersonOutlineOutlinedIcon />, roles: ["user", "viewer", "analyst", "admin"] },
  { label: "How It Works", path: "/how-it-works", icon: <HelpOutlineOutlinedIcon />, roles: ["user", "viewer", "analyst", "admin"] },
  { label: "Worker Health", path: "/admin/workers", icon: <TimelineOutlinedIcon />, roles: ["admin"] },
];

export function AppLayout() {
  const location = useLocation();
  const { user, logout } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);

  function navigation() {
    const availableItems = navItems.filter((item) => user && item.roles.includes(user.role));

    return (
      <>
        <Toolbar sx={{ px: 2.25, minHeight: "64px !important" }}>
          <Stack direction="row" spacing={1} alignItems="center">
            <DirectionsRunOutlinedIcon sx={{ color: "var(--gk-cyan)" }} fontSize="small" />
            <Typography className="gk-editorial" variant="subtitle1" fontWeight={650} color="var(--gk-shell-text)">
              Bear A Hand Sports
            </Typography>
          </Stack>
        </Toolbar>
        <Divider />
        <List sx={{ px: 1.25, py: 1.75 }}>
          {availableItems.map((item) => (
            <ListItemButton
              key={item.path}
              component={RouterLink}
              to={item.path}
              selected={location.pathname === item.path || location.pathname.startsWith(`${item.path}/`)}
              aria-current={location.pathname === item.path || location.pathname.startsWith(`${item.path}/`) ? "page" : undefined}
              onClick={() => setMobileOpen(false)}
              sx={{
                minHeight: 42,
                px: 1.5,
                py: 0.75,
                mb: 0.75,
                borderRadius: "var(--gk-radius-sm)",
                color: "var(--gk-shell-text-secondary)",
                border: "1px solid transparent",
                "&.Mui-selected": {
                  color: "var(--gk-cyan)",
                  backgroundColor: "var(--gk-gold-soft)",
                  borderColor: "rgba(0, 212, 255, 0.28)",
                },
                "&.Mui-selected:hover": {
                  backgroundColor: "rgba(0, 212, 255, 0.16)",
                },
                "&:hover": {
                  color: "var(--gk-shell-text)",
                  backgroundColor: "rgba(243, 238, 227, 0.04)",
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
          backgroundColor: "var(--gk-shell)",
          color: "var(--gk-shell-text)",
          boxShadow: "none",
        }}
      >
        <Toolbar sx={{ minHeight: "56px !important", px: { xs: 1.5, sm: 2.25 }, justifyContent: "space-between" }}>
          <Stack direction="row" spacing={1.2} alignItems="center">
            <IconButton aria-label="Open navigation" sx={{ display: { sm: "none" }, color: "var(--gk-cyan)" }} onClick={() => setMobileOpen((value) => !value)}>
              <MenuOutlinedIcon />
            </IconButton>
            <Stack>
              <Typography data-testid="sports-intelligence-title" className="gk-editorial" variant="subtitle1" fontWeight={650} sx={{ color: "var(--gk-shell-text)", lineHeight: 1.15 }}>Sports Intelligence</Typography>
              <Typography variant="caption" sx={{ color: "var(--gk-shell-text-secondary)" }}>Daily model intelligence · {user?.role ?? "user"}</Typography>
            </Stack>
          </Stack>
          <Stack direction="row" spacing={0.5} alignItems="center">
            <ThemeToggleButton />
            <IconButton aria-label="Sign Out" onClick={logout} sx={{ color: "var(--gk-cyan)" }}>
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
            backgroundColor: "var(--gk-shell)",
            color: "var(--gk-shell-text)",
            boxShadow: "var(--gk-shadow-md)",
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
            borderRightColor: "var(--gk-border)",
            backgroundColor: "var(--gk-shell)",
            color: "var(--gk-shell-text)",
          },
        }}
      >
        {navigation()}
      </Drawer>

      <Box component="main" sx={{ flexGrow: 1, minWidth: 0, p: { xs: 2, sm: 2.25 }, pb: { xs: "calc(88px + env(safe-area-inset-bottom))", sm: 2.25 }, mt: 7 }}>
        <Outlet />
        <Box component="footer" sx={{ mt: 2.5, pt: 1.5, borderTop: "1px solid", borderTopColor: "divider" }}>
          <Typography variant="caption" color="text.secondary">
            Bear A Hand Sports Intelligence
          </Typography>
          <CustomerLinks />
        </Box>
      </Box>
      <MobileNav />
    </Box>
  );
}
