import { fireEvent, render, screen } from "@testing-library/react";
import { useTheme } from "@mui/material";
import { beforeEach, describe, expect, it } from "vitest";

import { ThemeToggleButton } from "../../src/components/ThemeToggleButton";
import { THEME_STORAGE_KEY } from "../../src/theme/ThemeModeContext";
import { ThemeModeProvider } from "../../src/theme/ThemeModeProvider";

function ThemeProbe() {
  const theme = useTheme();
  return <span data-testid="theme-mode">{theme.palette.mode}</span>;
}

function renderTheme() {
  return render(
    <ThemeModeProvider>
      <ThemeProbe />
      <ThemeToggleButton />
    </ThemeModeProvider>,
  );
}

describe("theme mode", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("defaults to dark and persists a light selection", () => {
    renderTheme();

    expect(screen.getByTestId("theme-mode").textContent).toBe("dark");
    fireEvent.click(screen.getByRole("button", { name: "Switch to light mode" }));

    expect(screen.getByTestId("theme-mode").textContent).toBe("light");
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe("light");
    expect(screen.getByRole("button", { name: "Switch to dark mode" })).toBeTruthy();
  });

  it("restores a saved dark preference on provider initialization", () => {
    localStorage.setItem(THEME_STORAGE_KEY, "dark");
    renderTheme();

    expect(screen.getByTestId("theme-mode").textContent).toBe("dark");
    expect(screen.getByRole("button", { name: "Switch to light mode" })).toBeTruthy();
    const rootStyles = getComputedStyle(document.documentElement);
    expect(rootStyles.getPropertyValue("--gk-bg").trim()).toBe("#060d14");
    expect(rootStyles.getPropertyValue("--gk-text").trim()).toBe("#edf4fa");
    expect(rootStyles.getPropertyValue("--gk-gold").trim()).toBe("#00d4ff");
    expect(rootStyles.getPropertyValue("--gk-analytics").trim()).toBe("#a4ef18");
    expect(rootStyles.getPropertyValue("--gk-premium").trim()).toBe("#00d4ff");
    expect(rootStyles.getPropertyValue("--gk-motion-normal").trim()).toBe("180ms");
    expect(rootStyles.getPropertyValue("--gk-font-editorial")).toContain("Newsreader Variable");
    expect(rootStyles.getPropertyValue("--gk-font-sans")).toContain("Manrope Variable");
    expect(rootStyles.getPropertyValue("--gk-font-mono")).toContain("IBM Plex Mono");
  });

  it("preserves a saved light preference", () => {
    localStorage.setItem(THEME_STORAGE_KEY, "light");
    renderTheme();
    expect(screen.getByTestId("theme-mode").textContent).toBe("light");
    expect(screen.getByRole("button", { name: "Switch to dark mode" })).toBeTruthy();
  });
});