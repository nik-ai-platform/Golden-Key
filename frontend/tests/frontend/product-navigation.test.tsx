import { render, screen, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { AuthContext } from "../../src/auth/AuthContextDefinition";
import { AppLayout } from "../../src/layouts/AppLayout";
import { ThemeModeProvider } from "../../src/theme/ThemeModeProvider";

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
    ).toEqual(["Dashboard", "Games", "Saved Picks", "Parlay Optimizer", "Performance", "Profile"]);
    expect(
      within(desktopNavigation)
        .getByRole("link", { name: "Games" })
        .getAttribute("aria-current"),
      ).toBe("page");
    expect(screen.getByRole("button", { name: "Open navigation" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Switch to dark mode" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Sign Out" })).toBeTruthy();
    expect(screen.queryByText(/Product API/)).toBeNull();

    for (const label of ["Dashboard", "Games", "Saved Picks", "Parlay Optimizer", "Performance", "Profile"]) {
      expect(screen.getAllByText(label).length).toBeGreaterThan(0);
    }
    expect(
      screen.getByRole("button", { name: "Games" }).getAttribute("aria-current"),
    ).toBe("page");
  });
});