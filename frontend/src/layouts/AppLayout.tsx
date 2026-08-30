import BookmarkBorderOutlinedIcon from "@mui/icons-material/BookmarkBorderOutlined";
import DashboardOutlinedIcon from "@mui/icons-material/DashboardOutlined";
import DirectionsRunOutlinedIcon from "@mui/icons-material/DirectionsRunOutlined";
import LogoutOutlinedIcon from "@mui/icons-material/LogoutOutlined";
import MenuOutlinedIcon from "@mui/icons-material/MenuOutlined";
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
import { Outlet, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../hooks/useAuth";
import { MobileNav } from "../components/MobileNav";

const drawerWidth = 270;

const navItems = [
  { label: "Dashboard", path: "/dashboard", icon: <DashboardOutlinedIcon />, roles: ["user", "viewer", "analyst", "admin"] },
  { label: "Games", path: "/games", icon: <SportsBasketballOutlinedIcon />, roles: ["user", "viewer", "analyst", "admin"] },
  { label: "Performance", path: "/performance", icon: <TimelineOutlinedIcon />, roles: ["user", "viewer", "analyst", "admin"] },
  { label: "Saved Picks", path: "/saved-picks", icon: <BookmarkBorderOutlinedIcon />, roles: ["user", "viewer", "analyst", "admin"] },
  { label: "Profile", path: "/profile", icon: <DashboardOutlinedIcon />, roles: ["user", "viewer", "analyst", "admin"] },
];

export function AppLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [mobileOpen, setMobileOpen] = useState(false);

  function handleNav(path: string) {
    navigate(path);
    setMobileOpen(false);
  }

  function navigation() {
    const availableItems = navItems.filter((item) => user && item.roles.includes(user.role));

    return (
      <>
        <Toolbar>
          <Stack direction="row" spacing={1.2} alignItems="center">
            <DirectionsRunOutlinedIcon />
            <Typography variant="h6" fontWeight={800}>Golden Key</Typography>
          </Stack>
        </Toolbar>
        <Divider sx={{ borderColor: "rgba(255,255,255,0.2)" }} />
        <List>
          {availableItems.map((item) => (
            <ListItemButton
              key={item.path}
              selected={location.pathname === item.path}
              onClick={() => handleNav(item.path)}
              sx={{
                mx: 1,
                my: 0.5,
                borderRadius: 2,
                "&.Mui-selected": { backgroundColor: "rgba(250, 204, 21, 0.2)" },
              }}
            >
              <ListItemIcon sx={{ color: "inherit", minWidth: 40 }}>{item.icon}</ListItemIcon>
              <ListItemText primary={item.label} />
            </ListItemButton>
          ))}
        </List>
      </>
    );
  }

  return (
    <Box sx={{ display: "flex", minHeight: "100vh", background: "linear-gradient(140deg, #f0fdfa 0%, #f8fafc 45%, #fefce8 100%)" }}>
      <AppBar
        position="fixed"
        color="inherit"
        elevation={0}
        sx={{ width: { sm: `calc(100% - ${drawerWidth}px)` }, ml: { sm: `${drawerWidth}px` }, borderBottom: "1px solid #dbe7ea" }}
      >
        <Toolbar sx={{ justifyContent: "space-between" }}>
          <Stack direction="row" spacing={1.2} alignItems="center">
            <IconButton sx={{ display: { sm: "none" } }} onClick={() => setMobileOpen((value) => !value)} color="primary">
              <MenuOutlinedIcon />
            </IconButton>
            <Stack>
              <Typography variant="h6">Sports Intelligence</Typography>
              <Typography variant="caption" color="text.secondary">Daily model intelligence · {user?.role ?? "user"}</Typography>
            </Stack>
          </Stack>
          <IconButton onClick={logout} color="primary">
            <LogoutOutlinedIcon />
          </IconButton>
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
            background: "linear-gradient(170deg, #0f766e 0%, #134e4a 100%)",
            color: "white",
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
            borderRight: "1px solid #dbe7ea",
            background: "linear-gradient(170deg, #0f766e 0%, #134e4a 100%)",
            color: "white",
          },
        }}
      >
        {navigation()}
      </Drawer>

      <Box component="main" sx={{ flexGrow: 1, p: { xs: 2, sm: 3 }, pb: { xs: 11, sm: 3 }, mt: 8 }}>
        <Outlet />
        <Box component="footer" sx={{ mt: 4, pt: 2, borderTop: "1px solid #dbe7ea" }}>
          <Typography variant="caption" color="text.secondary">
            Golden Key · Product API v1
          </Typography>
        </Box>
      </Box>
      <MobileNav />
    </Box>
  );
}
