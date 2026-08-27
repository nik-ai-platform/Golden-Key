import { createTheme } from "@mui/material";

export const theme = createTheme({
  palette: {
    mode: "light",
    primary: {
      main: "#0f766e",
    },
    secondary: {
      main: "#ca8a04",
    },
    background: {
      default: "#f8fafc",
      paper: "#ffffff",
    },
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
