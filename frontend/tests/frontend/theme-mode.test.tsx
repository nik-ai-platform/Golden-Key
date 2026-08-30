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

  it("defaults to light and persists a dark selection", () => {
    renderTheme();

    expect(screen.getByTestId("theme-mode").textContent).toBe("light");
    fireEvent.click(screen.getByRole("button", { name: "Switch to dark mode" }));

    expect(screen.getByTestId("theme-mode").textContent).toBe("dark");
    expect(localStorage.getItem(THEME_STORAGE_KEY)).toBe("dark");
    expect(screen.getByRole("button", { name: "Switch to light mode" })).toBeTruthy();
  });

  it("restores a saved dark preference on provider initialization", () => {
    localStorage.setItem(THEME_STORAGE_KEY, "dark");
    renderTheme();

    expect(screen.getByTestId("theme-mode").textContent).toBe("dark");
    expect(screen.getByRole("button", { name: "Switch to light mode" })).toBeTruthy();
  });
});