import { CssBaseline, ThemeProvider } from "@mui/material";
import type { PaletteMode } from "@mui/material";
import { useMemo, useState } from "react";
import type { PropsWithChildren } from "react";

import { createAppTheme } from "../theme";
import { THEME_STORAGE_KEY, ThemeModeContext } from "./ThemeModeContext";

function initialMode(): PaletteMode {
  const storedMode = localStorage.getItem(THEME_STORAGE_KEY);
  return storedMode === "dark" || storedMode === "light" ? storedMode : "light";
}

export function ThemeModeProvider({ children }: PropsWithChildren) {
  const [mode, setMode] = useState<PaletteMode>(initialMode);
  const theme = useMemo(() => createAppTheme(mode), [mode]);

  function toggleTheme() {
    setMode((currentMode) => {
      const nextMode = currentMode === "light" ? "dark" : "light";
      localStorage.setItem(THEME_STORAGE_KEY, nextMode);
      return nextMode;
    });
  }

  return (
    <ThemeModeContext.Provider value={{ mode, toggleTheme }}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        {children}
      </ThemeProvider>
    </ThemeModeContext.Provider>
  );
}