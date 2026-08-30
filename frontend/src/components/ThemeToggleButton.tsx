import DarkModeOutlinedIcon from "@mui/icons-material/DarkModeOutlined";
import LightModeOutlinedIcon from "@mui/icons-material/LightModeOutlined";
import { IconButton, Tooltip } from "@mui/material";

import { useThemeMode } from "../theme/ThemeModeContext";

export function ThemeToggleButton() {
  const { mode, toggleTheme } = useThemeMode();
  const label = mode === "light" ? "Switch to dark mode" : "Switch to light mode";

  return (
    <Tooltip title={label}>
      <IconButton aria-label={label} onClick={toggleTheme} color="inherit">
        {mode === "light" ? <DarkModeOutlinedIcon /> : <LightModeOutlinedIcon />}
      </IconButton>
    </Tooltip>
  );
}