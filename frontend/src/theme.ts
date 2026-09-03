import { createTheme } from "@mui/material";
import type { PaletteMode } from "@mui/material";

const darkTokens = {
  "--gk-bg": "#090b0f",
  "--gk-surface": "#11151b",
  "--gk-surface-raised": "#171c24",
  "--gk-surface-soft": "#1c2130",
  "--gk-text": "#f7f8fa",
  "--gk-text-secondary": "#a5acb8",
  "--gk-text-muted": "#727b89",
  "--gk-border": "rgba(255, 255, 255, 0.08)",
  "--gk-border-strong": "rgba(255, 255, 255, 0.14)",
};

const lightTokens = {
  "--gk-bg": "#f4f5f7",
  "--gk-surface": "#ffffff",
  "--gk-surface-raised": "#ffffff",
  "--gk-surface-soft": "#eceff3",
  "--gk-text": "#11151b",
  "--gk-text-secondary": "#586170",
  "--gk-text-muted": "#727b89",
  "--gk-border": "rgba(17, 21, 27, 0.10)",
  "--gk-border-strong": "rgba(17, 21, 27, 0.18)",
};

const brandTokens = {
  "--gk-gold": "#d6ad45",
  "--gk-gold-bright": "#f0c75e",
  "--gk-gold-soft": "rgba(214, 173, 69, 0.14)",
  "--gk-analytics": "#2dd4a7",
  "--gk-analytics-soft": "rgba(45, 212, 167, 0.12)",
  "--gk-premium": "#8b7cf6",
  "--gk-premium-soft": "rgba(139, 124, 246, 0.12)",
  "--gk-win": "#3ddc97",
  "--gk-loss": "#f05d68",
  "--gk-warning": "#f2b84b",
  "--gk-radius-sm": "8px",
  "--gk-radius-md": "12px",
  "--gk-radius-lg": "18px",
  "--gk-motion-fast": "150ms",
  "--gk-motion-normal": "240ms",
  "--gk-motion-slow": "420ms",
};

export function createAppTheme(mode: PaletteMode) {
  const modeTokens = mode === "dark" ? darkTokens : lightTokens;

  return createTheme({
    palette: {
      mode,
      primary: {
        main: mode === "dark" ? "#d6ad45" : "#8a6818",
        contrastText: mode === "dark" ? "#090b0f" : "#ffffff",
      },
      secondary: {
        main: mode === "dark" ? "#8b7cf6" : "#6555d9",
      },
      info: {
        main: mode === "dark" ? "#2dd4a7" : "#087f69",
      },
      success: {
        main: mode === "dark" ? "#3ddc97" : "#16875c",
      },
      error: {
        main: mode === "dark" ? "#f05d68" : "#c83b49",
      },
      warning: {
        main: mode === "dark" ? "#f2b84b" : "#9a6500",
      },
      background: {
        default: modeTokens["--gk-bg"],
        paper: modeTokens["--gk-surface"],
      },
      text: {
        primary: modeTokens["--gk-text"],
        secondary: modeTokens["--gk-text-secondary"],
      },
      divider: modeTokens["--gk-border"],
    },
    shape: {
      borderRadius: 8,
    },
    typography: {
      fontFamily: "'Aptos', 'Trebuchet MS', sans-serif",
      h4: {
        fontWeight: 800,
        letterSpacing: 0,
      },
      h5: {
        fontWeight: 700,
        letterSpacing: 0,
      },
      button: {
        fontWeight: 700,
        letterSpacing: 0,
        textTransform: "none",
      },
    },
    components: {
      MuiCssBaseline: {
        styleOverrides: {
          ":root": {
            ...brandTokens,
            ...modeTokens,
            colorScheme: mode,
          },
          body: {
            backgroundColor: "var(--gk-bg)",
            color: "var(--gk-text)",
          },
          ".gk-card": {
            transition: [
              "transform var(--gk-motion-normal) ease",
              "border-color var(--gk-motion-normal) ease",
              "box-shadow var(--gk-motion-normal) ease",
            ].join(", "),
          },
          ".gk-card:hover": {
            transform: "translateY(-2px)",
            borderColor: "var(--gk-border-strong)",
          },
          ".gk-best-bet": {
            animation: "gk-best-bet-enter var(--gk-motion-slow) ease-out",
          },
          "@keyframes gk-best-bet-enter": {
            from: {
              opacity: 0,
              transform: "translateY(10px) scale(0.99)",
            },
            to: {
              opacity: 1,
              transform: "translateY(0) scale(1)",
            },
          },
          "@media (prefers-reduced-motion: reduce)": {
            ".gk-card, .gk-best-bet": {
              animation: "none",
              transition: "none",
            },
          },
        },
      },
      MuiCard: {
        styleOverrides: {
          root: {
            backgroundImage: "none",
            borderColor: "var(--gk-border)",
            borderRadius: "var(--gk-radius-sm)",
          },
        },
      },
      MuiToolbar: {
        styleOverrides: {
          root: {
            minHeight: 56,
          },
        },
      },
      MuiToggleButton: {
        styleOverrides: {
          root: {
            minHeight: 34,
            padding: "5px 12px",
          },
        },
      },
      MuiButton: {
        defaultProps: {
          disableElevation: true,
        },
      },
    },
  });
}
