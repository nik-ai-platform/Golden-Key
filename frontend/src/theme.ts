import { createTheme } from "@mui/material";
import type { PaletteMode } from "@mui/material";

export function createAppTheme(mode: PaletteMode) {
  return createTheme({
  palette: {
    mode,
    primary: {
      main: mode === "light" ? "#0f766e" : "#5eead4",
    },
    secondary: {
      main: mode === "light" ? "#ca8a04" : "#facc15",
    },
    background: {
      default: mode === "light" ? "#f8fafc" : "#071312",
      paper: mode === "light" ? "#ffffff" : "#102321",
    },
    divider: mode === "light" ? "#dbe7ea" : "rgba(148, 163, 184, 0.28)",
  },
  shape: {
    borderRadius: 14,
  },
  typography: {
    fontFamily: "'Trebuchet MS', 'Segoe UI', sans-serif",
    h4: {
      fontWeight: 800,
      letterSpacing: 0.2,
    },
    h5: {
      fontWeight: 700,
    },
  },
  });
}
