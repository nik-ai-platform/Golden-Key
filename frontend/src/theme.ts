import { createTheme } from "@mui/material";
import type { PaletteMode } from "@mui/material";

const darkTokens = {
  "--gk-bg": "#0b0d10",
  "--gk-surface": "#12161b",
  "--gk-surface-raised": "#171c22",
  "--gk-surface-soft": "#1b2027",
  "--gk-text": "#f3eee3",
  "--gk-text-secondary": "#98a1ae",
  "--gk-text-muted": "#717b88",
  "--gk-border": "rgba(243, 238, 227, 0.08)",
  "--gk-border-strong": "rgba(243, 238, 227, 0.16)",
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
  "--gk-shell": "#0b0d10",
  "--gk-shell-raised": "#12161b",
  "--gk-shell-text": "#f3eee3",
  "--gk-shell-text-secondary": "#98a1ae",
  "--gk-gold": "#c6a15b",
  "--gk-gold-bright": "#d8b875",
  "--gk-gold-soft": "rgba(198, 161, 91, 0.12)",
  "--gk-analytics": "#22c58b",
  "--gk-analytics-soft": "rgba(34, 197, 139, 0.11)",
  "--gk-premium": "#8b7cf6",
  "--gk-premium-soft": "rgba(139, 124, 246, 0.12)",
  "--gk-win": "#22c58b",
  "--gk-loss": "#f05d68",
  "--gk-warning": "#f2b84b",
  "--gk-radius-sm": "12px",
  "--gk-radius-md": "14px",
  "--gk-radius-lg": "16px",
  "--gk-shadow-sm": "0 8px 24px rgba(0, 0, 0, 0.18)",
  "--gk-shadow-md": "0 18px 44px rgba(0, 0, 0, 0.24)",
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

  return createTheme({
    palette: {
      mode,
      primary: {
        main: mode === "dark" ? "#c6a15b" : "#80601f",
        contrastText: mode === "dark" ? "#0b0d10" : "#ffffff",
      },
      secondary: {
        main: mode === "dark" ? "#8b7cf6" : "#6555d9",
      },
      info: {
        main: mode === "dark" ? "#22c58b" : "#087f69",
      },
      success: {
        main: mode === "dark" ? "#22c58b" : "#16875c",
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
            colorScheme: mode,
          },
          body: {
            backgroundColor: "var(--gk-bg)",
            color: "var(--gk-text)",
            fontVariantNumeric: "tabular-nums",
          },
          ".gk-editorial": {
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
            transition: "color var(--gk-motion-fast) var(--gk-ease), background-color var(--gk-motion-fast) var(--gk-ease), border-color var(--gk-motion-fast) var(--gk-ease)",
          },
        },
      },
      MuiButton: {
        defaultProps: {
          disableElevation: true,
        },
        styleOverrides: {
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
