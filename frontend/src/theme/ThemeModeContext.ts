import type { PaletteMode } from "@mui/material";
import { createContext, useContext } from "react";

export const THEME_STORAGE_KEY = "golden-key-theme";

export type ThemeModeContextValue = {
  mode: PaletteMode;
  toggleTheme: () => void;
};

export const ThemeModeContext = createContext<
  ThemeModeContextValue | undefined
>(undefined);

export function useThemeMode() {
  const context = useContext(ThemeModeContext);
  if (!context) {
    throw new Error("useThemeMode must be used inside ThemeModeProvider");
  }
  return context;
}