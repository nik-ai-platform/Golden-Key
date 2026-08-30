import { render, screen } from "@testing-library/react";
import { MemoryRouter, Outlet } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { AuthContext } from "../../src/auth/AuthContextDefinition";
import { AppRouter } from "../../src/routes/AppRouter";
import { ThemeModeProvider } from "../../src/theme/ThemeModeProvider";

vi.mock("../../src/layouts/AppLayout", () => ({
  AppLayout: () => <Outlet />,
}));

vi.mock("../../src/pages/ProductDashboardPage", () => ({
  ProductDashboardPage: () => <h1>Production dashboard</h1>,
}));

const auth = {
  user: { id: 1, email: "user@example.com", username: "user", role: "user" as const },
  isAuthenticated: true,
  isBootstrapping: false,
  login: vi.fn(),
  logout: vi.fn(),
};

function renderRoute(path: string) {
  return render(
    <ThemeModeProvider>
      <AuthContext.Provider value={auth}>
        <MemoryRouter initialEntries={[path]}>
          <AppRouter />
        </MemoryRouter>
      </AuthContext.Provider>
    </ThemeModeProvider>,
  );
}

describe("production route surface", () => {
  it.each(["/product", "/product/live", "/product/settings"])(
    "redirects the legacy %s route to the dashboard",
    async (path) => {
      renderRoute(path);

      expect(await screen.findByRole("heading", { name: "Production dashboard" })).toBeTruthy();
      expect(screen.queryByText("Product Experience Preview")).toBeNull();
    },
  );

  it.each([
    "/assistant",
    "/community",
    "/portfolio",
    "/simulator",
    "/sports-brain",
    "/onboarding",
    "/teams",
    "/analytics",
    "/predictions",
    "/models",
    "/admin/pipeline",
  ])(
    "does not expose the removed %s route",
    async (path) => {
      renderRoute(path);

      expect(await screen.findByRole("heading", { name: "Page not found" })).toBeTruthy();
    },
  );
});