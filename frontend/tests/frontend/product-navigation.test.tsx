import { render, screen, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { AuthContext } from "../../src/auth/AuthContextDefinition";
import { AppLayout } from "../../src/layouts/AppLayout";
import { ThemeModeProvider } from "../../src/theme/ThemeModeProvider";
import { styleAtBreakpoint } from "./responsiveStyles";

const auth = {
  user: { id: 1, email: "user@example.com", username: "user", role: "user" as const },
  isAuthenticated: true,
  isBootstrapping: false,
  login: vi.fn(),
  logout: vi.fn(),
};

describe("product navigation", () => {
  it("uses the approved order, semantic links, and nested Games state", () => {
    render(
      <ThemeModeProvider>
        <AuthContext.Provider value={auth}>
          <MemoryRouter initialEntries={["/games/101"]}>
            <Routes>
              <Route element={<AppLayout />}>
                <Route path="/games/:gameId" element={<div>Game detail</div>} />
              </Route>
            </Routes>
          </MemoryRouter>
        </AuthContext.Provider>
      </ThemeModeProvider>,
    );

    const desktopNavigation = screen.getByRole("list");
    expect(
      within(desktopNavigation).getAllByRole("link").map((link) => link.textContent),
    ).toEqual(["Dashboard", "Games", "Saved Picks", "Parlay Optimizer", "Performance", "Profile", "How It Works"]);
    expect(
      within(desktopNavigation)
        .getByRole("link", { name: "Games" })
        .getAttribute("aria-current"),
      ).toBe("page");
    expect(screen.getByRole("button", { name: "Open navigation" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Switch to light mode" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Sign Out" })).toBeTruthy();
    expect(getComputedStyle(document.documentElement).getPropertyValue("--gk-shell-text").trim()).toBe("#edf4fa");
    const artwork = screen.getByRole("img", { name: /Bear A Hand Sports artwork featuring the bear/ });
    expect(artwork.getAttribute("src")).toBe("/Bear_A_Hand_Sports_FullColor.jpg");
    expect(screen.getByRole("img", { name: "Bear A Hand Sports wordmark" }).getAttribute("src")).toBe("/Bear_A_Hand_Sports_Wordmark.png");
    expect(screen.queryByText("Sports Intelligence")).toBeNull();
    expect(screen.queryByText(/Daily model intelligence/)).toBeNull();
    expect(screen.queryByText(/Product API/)).toBeNull();

    for (const label of ["Dashboard", "Games", "Saved Picks", "Parlay Optimizer", "Performance", "Profile"]) {
      expect(screen.getAllByText(label).length).toBeGreaterThan(0);
    }
    expect(
      screen.getByRole("button", { name: "Games" }).getAttribute("aria-current"),
    ).toBe("page");
    const main = screen.getByRole("main");
    expect(styleAtBreakpoint(main, 0, "margin-top")).toBe("194px");
    expect(styleAtBreakpoint(main, 600, "margin-top")).toBe("234px");
    expect(styleAtBreakpoint(main, 900, "margin-top")).toBe("250px");
    expect(styleAtBreakpoint(main, 0, "padding-bottom")).toBe("calc(88px + env(safe-area-inset-bottom))");
    expect(styleAtBreakpoint(main, 600, "padding-bottom")).toBe("18px");
    const nav = screen.getByTestId("mobile-navigation-shell");
    expect(nav.dataset.safeArea).toBe("bottom");
    expect(88).toBeGreaterThan(Number.parseFloat(getComputedStyle(screen.getByRole("button", { name: "Games" })).minHeight));
  });
});