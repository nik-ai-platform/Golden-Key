import AssessmentOutlinedIcon from "@mui/icons-material/AssessmentOutlined";
import BookmarkBorderOutlinedIcon from "@mui/icons-material/BookmarkBorderOutlined";
import CasinoOutlinedIcon from "@mui/icons-material/CasinoOutlined";
import DashboardOutlinedIcon from "@mui/icons-material/DashboardOutlined";
import PersonOutlineOutlinedIcon from "@mui/icons-material/PersonOutlineOutlined";
import SportsBasketballOutlinedIcon from "@mui/icons-material/SportsBasketballOutlined";
import { BottomNavigation, BottomNavigationAction, Paper } from "@mui/material";
import { useLocation, useNavigate } from "react-router-dom";

const items = [
  { label: "Dashboard", path: "/dashboard", icon: <DashboardOutlinedIcon /> },
  { label: "Games", path: "/games", icon: <SportsBasketballOutlinedIcon /> },
  { label: "Saved Picks", path: "/saved-picks", icon: <BookmarkBorderOutlinedIcon /> },
  { label: "Parlays", path: "/parlays", icon: <CasinoOutlinedIcon /> },
  { label: "Performance", path: "/performance", icon: <AssessmentOutlinedIcon /> },
  { label: "Profile", path: "/profile", icon: <PersonOutlineOutlinedIcon /> },
];

export function MobileNav() {
  const location = useLocation();
  const navigate = useNavigate();
  const activePath = items.find((item) => location.pathname.startsWith(item.path))?.path ?? false;

  return (
    <Paper
      data-testid="mobile-navigation-shell"
      data-safe-area="bottom"
      elevation={0}
      sx={{
        display: { xs: "block", sm: "none" },
        position: "fixed",
        left: 0,
        right: 0,
        bottom: 0,
        zIndex: (theme) => theme.zIndex.appBar,
        borderTop: "1px solid var(--gk-border-strong)",
        backgroundColor: "var(--gk-shell)",
        paddingBottom: "env(safe-area-inset-bottom)",
      }}
    >
      <BottomNavigation
        showLabels
        value={activePath}
        onChange={(_, path: string) => navigate(path)}
        sx={{
          overflowX: "auto",
          overflowY: "hidden",
          justifyContent: "flex-start",
          "&::-webkit-scrollbar": {
            display: "none",
          },
          scrollbarWidth: "none",
          height: 58,
          minHeight: 58,
          backgroundColor: "transparent",
        }}
      >
        {items.map((item) => (
          <BottomNavigationAction
            key={item.path}
            value={item.path}
            label={item.label}
            icon={item.icon}
            aria-current={activePath === item.path ? "page" : undefined}
            sx={{
              minWidth: 68,
              flexShrink: 0,
              minHeight: 58,
              borderTop: "2px solid transparent",
              color: "var(--gk-shell-text-secondary)",
              "&.Mui-selected": {
                color: "var(--gk-cyan)",
                backgroundColor: "var(--gk-gold-soft)",
                borderTopColor: "var(--gk-gold)",
              },
              "& .MuiBottomNavigationAction-label": {
                fontFamily: "var(--gk-font-sans)",
                fontSize: "0.64rem",
                fontWeight: 700,
                "&.Mui-selected": { fontSize: "0.64rem" },
              },
            }}
          />
        ))}
      </BottomNavigation>
    </Paper>
  );
}
