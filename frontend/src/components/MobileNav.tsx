import AssessmentOutlinedIcon from "@mui/icons-material/AssessmentOutlined";
import BookmarkBorderOutlinedIcon from "@mui/icons-material/BookmarkBorderOutlined";
import DashboardOutlinedIcon from "@mui/icons-material/DashboardOutlined";
import PersonOutlineOutlinedIcon from "@mui/icons-material/PersonOutlineOutlined";
import SportsBasketballOutlinedIcon from "@mui/icons-material/SportsBasketballOutlined";
import { BottomNavigation, BottomNavigationAction, Paper } from "@mui/material";
import { useLocation, useNavigate } from "react-router-dom";

const items = [
  { label: "Dashboard", path: "/dashboard", icon: <DashboardOutlinedIcon /> },
  { label: "Games", path: "/games", icon: <SportsBasketballOutlinedIcon /> },
  { label: "Saved Picks", path: "/saved-picks", icon: <BookmarkBorderOutlinedIcon /> },
  { label: "Performance", path: "/performance", icon: <AssessmentOutlinedIcon /> },
  { label: "Profile", path: "/profile", icon: <PersonOutlineOutlinedIcon /> },
];

export function MobileNav() {
  const location = useLocation();
  const navigate = useNavigate();
  const activePath = items.find((item) => location.pathname.startsWith(item.path))?.path ?? false;

  return (
    <Paper elevation={8} sx={{ display: { xs: "block", sm: "none" }, position: "fixed", left: 0, right: 0, bottom: 0, zIndex: (theme) => theme.zIndex.appBar }}>
      <BottomNavigation showLabels value={activePath} onChange={(_, path: string) => navigate(path)}>
        {items.map((item) => (
          <BottomNavigationAction
            key={item.path}
            value={item.path}
            label={item.label}
            icon={item.icon}
            aria-current={activePath === item.path ? "page" : undefined}
          />
        ))}
      </BottomNavigation>
    </Paper>
  );
}
