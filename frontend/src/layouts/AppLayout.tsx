import BookmarkBorderOutlinedIcon from "@mui/icons-material/BookmarkBorderOutlined";
import CasinoOutlinedIcon from "@mui/icons-material/CasinoOutlined";
import CloseOutlinedIcon from "@mui/icons-material/CloseOutlined";
import DashboardOutlinedIcon from "@mui/icons-material/DashboardOutlined";
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

  function navigation(label: string, mobile = false) {
    const availableItems = navItems.filter((item) => user && item.roles.includes(user.role));

    return (
      <Box
        component="nav"
        aria-label={label}
        sx={{
          height: mobile ? "auto" : "100%",
          maxHeight: mobile ? "calc(100dvh - 24px)" : undefined,
          overflowY: "auto",
          overscrollBehavior: "contain",
        }}
      >
        <Toolbar
          sx={{
            px: mobile ? 2 : 2.25,
            minHeight: mobile ? "66px !important" : "64px !important",
            justifyContent: mobile ? "space-between" : "center",
          }}
        >
          <Box
            component="img"
            src="/Bear_A_Hand_Sports_Wordmark.png"
            alt="Bear A Hand Sports wordmark"
            width={168}
            height={38}
            sx={{ display: "block", width: "100%", maxWidth: 168, height: "auto", objectFit: "contain" }}
          />
          {mobile ? (
            <IconButton
              aria-label="Close navigation"
              onClick={() => setMobileOpen(false)}
              sx={{
                color: "#c4d4e0",
                borderRadius: "10px",
                "&:hover": {
                  color: "#edf4fa",
                  backgroundColor: "rgba(0, 212, 255, 0.09)",
                },
                "&:focus-visible": {
                  outline: "2px solid var(--gk-cyan)",
                  outlineOffset: 2,
                },
              }}
            >
              <CloseOutlinedIcon />
            </IconButton>
          ) : null}
        </Toolbar>
        <Divider sx={{ borderColor: "rgba(0, 212, 255, 0.16)" }} />
        <List sx={{ px: 1.5, py: mobile ? 1.25 : 2 }}>
          {availableItems.map((item) => {
            const selected =
              location.pathname === item.path ||
              location.pathname.startsWith(`${item.path}/`);
            return (
              <ListItemButton
                key={item.path}
                component={RouterLink}
                to={item.path}
                selected={selected}
                aria-current={selected ? "page" : undefined}
                onClick={() => setMobileOpen(false)}
                sx={{
                  minHeight: mobile ? 44 : 42,
                  px: 1.5,
                  py: mobile ? 0.7 : 0.75,
                  mb: mobile ? 0.5 : 0.75,
                  borderRadius: mobile ? "12px" : "var(--gk-radius-sm)",
                  border: mobile ? 0 : "1px solid transparent",
                  color: "var(--gk-shell-text-secondary)",
                  "&.Mui-selected": {
                    color: mobile ? "#06111b" : "var(--gk-cyan)",
                    backgroundColor: mobile ? "var(--gk-cyan)" : "var(--gk-gold-soft)",
                    border: mobile ? 0 : "1px solid rgba(0, 212, 255, 0.28)",
                    boxShadow: mobile
                      ? "0 4px 16px rgba(0, 212, 255, 0.22), inset 0 1px 0 rgba(255, 255, 255, 0.2)"
                      : "none",
                  },
                  "&.Mui-selected:hover": {
                    backgroundColor: mobile ? "#36ddff" : "rgba(0, 212, 255, 0.16)",
                  },
                  "&.Mui-focusVisible": {
                    outline: "2px solid var(--gk-cyan)",
                    outlineOffset: 2,
                  },
                  "&:hover": {
                    color: "var(--gk-shell-text)",
                    backgroundColor: mobile ? "rgba(0, 212, 255, 0.09)" : "rgba(243, 238, 227, 0.04)",
                  },
                }}
              >
                <ListItemIcon
                  sx={{
                    color: "inherit",
                    minWidth: mobile ? 38 : 34,
                    "& .MuiSvgIcon-root": { fontSize: mobile ? 20 : 19 },
                  }}
                >
                  {item.icon}
                </ListItemIcon>
                <ListItemText
                  primary={item.label}
                  primaryTypographyProps={{
                    variant: "body2",
                    fontWeight: mobile ? 650 : 750,
                    letterSpacing: mobile ? "0.01em" : undefined,
                    lineHeight: mobile ? 1.25 : undefined,
                  }}
                />
              </ListItemButton>
            );
          })}
        </List>
      </Box>
    );
  }

  return (
    <Box sx={{ display: "flex", minHeight: "100vh", backgroundColor: "background.default" }}>
      <AppBar
        data-testid="fixed-brand-header"
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
        <Toolbar data-testid="header-controls" sx={{ minHeight: "56px !important", px: { xs: 1.5, sm: 2.25 }, justifyContent: "space-between" }}>
          <Stack direction="row" spacing={1.2} alignItems="center">
            <IconButton aria-label="Open navigation" aria-expanded={mobileOpen} sx={{ display: { sm: "none" }, color: "var(--gk-cyan)" }} onClick={() => setMobileOpen((value) => !value)}>
              <MenuOutlinedIcon />
            </IconButton>
          </Stack>
          <Stack direction="row" spacing={0.5} alignItems="center">
            <ThemeToggleButton />
            <IconButton aria-label="Sign Out" onClick={logout} sx={{ color: "var(--gk-cyan)" }}>
              <LogoutOutlinedIcon />
            </IconButton>
          </Stack>
        </Toolbar>
        <Box
          data-testid="brand-artwork-banner"
          sx={{
            height: { xs: 88, sm: 112, md: 188 },
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            overflow: "hidden",
            background: "linear-gradient(100deg, #06111b 0%, #0a1b29 50%, #071521 100%)",
            borderTop: "1px solid rgba(0, 212, 255, 0.34)",
            px: { xs: 1, sm: 2, md: 3 },
          }}
        >
          <Box
            component="img"
            src="/Bear_A_Hand_Sports_Wordmark.png"
            alt="Original metallic Bear A Hand Sports wordmark"
            sx={{
              display: "block",
              width: "96%",
              maxWidth: 1100,
              height: "90%",
              minWidth: 0,
              minHeight: 0,
              objectFit: "contain",
            }}
          />
        </Box>
      </AppBar>

      <Drawer
        variant="temporary"
        open={mobileOpen}
        onClose={() => setMobileOpen(false)}
        sx={{
          display: { xs: "block", sm: "none" },
          "& .MuiBackdrop-root": {
            backgroundColor: "rgba(6, 13, 20, 0.86)",
          },
          [`& .MuiDrawer-paper`]: {
            width: "min(84vw, 336px)",
            boxSizing: "border-box",
            background: "linear-gradient(155deg, #0b1823 0%, #091722 54%, #07131e 100%)",
            color: "var(--gk-shell-text)",
            top: 12,
            bottom: "auto",
            left: 12,
            height: "auto",
            maxHeight: "calc(100dvh - 24px)",
            border: "1px solid rgba(0, 212, 255, 0.24)",
            borderRadius: "20px",
            overflow: "hidden",
            boxShadow:
              "0 24px 64px rgba(0, 0, 0, 0.62), 0 0 0 1px rgba(0, 212, 255, 0.07), 0 0 28px rgba(0, 212, 255, 0.12), inset 0 1px 0 rgba(255, 255, 255, 0.05)",
          },
        }}
      >
        {navigation("Mobile navigation", true)}
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
        {navigation("Primary navigation")}
      </Drawer>

      <Box component="main" sx={{ flexGrow: 1, minWidth: 0, p: { xs: 2, sm: 2.25 }, pb: { xs: "calc(88px + env(safe-area-inset-bottom))", sm: 2.25 }, mt: { xs: "146px", sm: "170px", md: "246px" } }}>
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
