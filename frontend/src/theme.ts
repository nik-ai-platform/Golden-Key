import { createTheme } from "@mui/material";
import type { PaletteMode } from "@mui/material";

const darkTokens = {
  "--gk-bg": "#060d14",
  "--gk-surface": "#0b1823",
  "--gk-surface-raised": "#102232",
  "--gk-surface-soft": "#0e2030",
  "--gk-text": "#edf4fa",
  "--gk-text-secondary": "#a9bccb",
  "--gk-text-muted": "#91a8ba",
  "--gk-border": "rgba(0, 212, 255, 0.18)",
  "--gk-border-strong": "rgba(0, 212, 255, 0.36)",
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
  "--gk-shell": "#060d14",
  "--gk-shell-raised": "#0b1823",
  "--gk-shell-text": "#edf4fa",
  "--gk-shell-text-secondary": "#a9bccb",
  "--gk-cyan": "#00d4ff",
  "--gk-lime": "#a4ef18",
  "--gk-gold": "#00d4ff",
  "--gk-gold-bright": "#00d4ff",
  "--gk-gold-soft": "rgba(0, 212, 255, 0.10)",
  "--gk-analytics": "#a4ef18",
  "--gk-analytics-soft": "rgba(164, 239, 24, 0.10)",
  "--gk-premium": "#00d4ff",
  "--gk-premium-soft": "rgba(0, 212, 255, 0.10)",
  "--gk-win": "#a4ef18",
  "--gk-loss": "#f05d68",
  "--gk-warning": "#f2b84b",
  "--gk-radius-sm": "8px",
  "--gk-radius-md": "10px",
  "--gk-radius-lg": "12px",
  "--gk-shadow-sm": "0 0 20px rgba(0, 212, 255, 0.06)",
  "--gk-shadow-md": "0 0 32px rgba(0, 212, 255, 0.10)",
  "--gk-motion-fast": "150ms",
  "--gk-motion-normal": "180ms",
  "--gk-motion-slow": "220ms",
  "--gk-ease": "cubic-bezier(0.2, 0.8, 0.2, 1)",
  "--gk-font-editorial": "\"Newsreader Variable\", Georgia, serif",
  "--gk-font-sans": "\"Manrope Variable\", \"Segoe UI\", sans-serif",
  "--gk-font-mono": "\"IBM Plex Mono\", \"SFMono-Regular\", Consolas, monospace",
};

export function createAppTheme(mode: PaletteMode) {
  const modeTokens = mode === "dark" ? darkTokens : lightTokens;
  const accentTokens = mode === "dark" ? {} : {
    "--gk-gold": "#00677d", "--gk-gold-bright": "#00677d",
    "--gk-analytics": "#466800", "--gk-premium": "#00677d",
  };

  return createTheme({
    palette: {
      mode,
      primary: {
        main: mode === "dark" ? "#00d4ff" : "#00677d",
        contrastText: mode === "dark" ? "#060d14" : "#ffffff",
      },
      secondary: {
        main: mode === "dark" ? "#a4ef18" : "#466800",
      },
      info: {
        main: mode === "dark" ? "#00d4ff" : "#00677d",
      },
      success: {
        main: mode === "dark" ? "#a4ef18" : "#466800",
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
      borderRadius: 12,
    },
    typography: {
      fontFamily: "var(--gk-font-sans)",
      allVariants: {
        fontVariantNumeric: "tabular-nums",
      },
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
      overline: {
        fontWeight: 750,
        letterSpacing: "0.06em",
      },
    },
    components: {
      MuiCssBaseline: {
        styleOverrides: {
          ":root": {
            ...brandTokens,
            ...modeTokens,
            ...accentTokens,
            colorScheme: mode,
          },
          body: {
            backgroundColor: "var(--gk-bg)",
            color: "var(--gk-text)",
            fontVariantNumeric: "tabular-nums",
          },
          ".gk-editorial, .gk-editorial.MuiTypography-root": {
            fontFamily: "var(--gk-font-editorial)",
          },
          ".gk-data, .gk-data.MuiTypography-root": {
            fontFamily: "var(--gk-font-mono)",
            fontVariantNumeric: "tabular-nums",
          },
          ".gk-card": {
            transition: [
              "transform var(--gk-motion-normal) var(--gk-ease)",
              "border-color var(--gk-motion-normal) var(--gk-ease)",
              "background-color var(--gk-motion-normal) var(--gk-ease)",
              "box-shadow var(--gk-motion-normal) var(--gk-ease)",
            ].join(", "),
          },
          ".gk-card:hover": {
            transform: "translateY(-1px)",
            borderColor: "var(--gk-border-strong)",
            boxShadow: "var(--gk-shadow-sm)",
          },
          ".gk-best-bet": {
            boxShadow: "var(--gk-shadow-sm)",
          },
          "@media (prefers-reduced-motion: reduce)": {
            "*, *::before, *::after": {
              scrollBehavior: "auto !important",
              animationDuration: "0.01ms !important",
              animationIterationCount: "1 !important",
              transitionDuration: "0.01ms !important",
            },
          },
        },
      },
      MuiCard: {
        styleOverrides: {
          root: {
            backgroundImage: "none",
            borderColor: "var(--gk-border)",
            borderRadius: "var(--gk-radius-md)",
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
            "&.Mui-selected": {
              color: mode === "dark" ? "#a4ef18" : "#466800",
              borderColor: mode === "dark" ? "#a4ef18" : "#466800",
              backgroundColor: "rgba(164, 239, 24, 0.10)",
            },
            transition: "color var(--gk-motion-fast) var(--gk-ease), background-color var(--gk-motion-fast) var(--gk-ease), border-color var(--gk-motion-fast) var(--gk-ease)",
          },
        },
      },
      MuiButton: {
        defaultProps: {
          disableElevation: true,
        },
        styleOverrides: {
          containedPrimary: {
            background: mode === "dark"
              ? "linear-gradient(110deg, #00d4ff, #48a8ff)"
              : "linear-gradient(110deg, #00677d, #1859a1)",
            "&:hover": { filter: "brightness(1.08)" },
            "&.Mui-disabled": { background: "none", filter: "none" },
          },
          root: {
            borderRadius: "var(--gk-radius-sm)",
            transition: "transform var(--gk-motion-fast) var(--gk-ease), color var(--gk-motion-fast) var(--gk-ease), background-color var(--gk-motion-fast) var(--gk-ease), border-color var(--gk-motion-fast) var(--gk-ease)",
            "&:active": { transform: "translateY(1px)" },
            "&:focus-visible": { outline: "2px solid var(--gk-gold)", outlineOffset: 2 },
          },
        },
      },
      MuiIconButton: {
        styleOverrides: {
          root: {
            transition: "transform var(--gk-motion-fast) var(--gk-ease), color var(--gk-motion-fast) var(--gk-ease), background-color var(--gk-motion-fast) var(--gk-ease)",
            "&:active": { transform: "translateY(1px)" },
            "&:focus-visible": { outline: "2px solid var(--gk-gold)", outlineOffset: 2 },
          },
        },
      },
      MuiListItemButton: {
        styleOverrides: {
          root: {
            transition: "color var(--gk-motion-normal) var(--gk-ease), background-color var(--gk-motion-normal) var(--gk-ease), border-color var(--gk-motion-normal) var(--gk-ease)",
            "&:focus-visible": { outline: "2px solid var(--gk-gold)", outlineOffset: 2 },
          },
        },
      },
      MuiTab: {
        styleOverrides: {
          root: {
            textTransform: "none",
            transition: "color var(--gk-motion-normal) var(--gk-ease), background-color var(--gk-motion-normal) var(--gk-ease)",
          },
        },
      },
      MuiBottomNavigationAction: {
        styleOverrides: {
          root: {
            color: "var(--gk-shell-text-secondary)",
            transition: "color var(--gk-motion-normal) var(--gk-ease), background-color var(--gk-motion-normal) var(--gk-ease)",
            "&.Mui-selected": {
              color: "var(--gk-gold-bright)",
            },
            "&:focus-visible": {
              outline: "2px solid var(--gk-gold)",
              outlineOffset: -2,
            },
          },
        },
      },
    },
  });
}
