import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi } from "vitest";

import { AuthContext } from "../../src/auth/AuthContextDefinition";
import { LoginPage } from "../../src/pages/LoginPage";
import { ThemeModeProvider } from "../../src/theme/ThemeModeProvider";

function renderLogin(login = vi.fn().mockResolvedValue(undefined)) {
  render(
    <ThemeModeProvider>
      <AuthContext.Provider
        value={{
          user: null,
          isAuthenticated: false,
          isBootstrapping: false,
          login,
          logout: vi.fn(),
        }}
      >
        <MemoryRouter initialEntries={["/login"]}>
          <LoginPage />
        </MemoryRouter>
      </AuthContext.Provider>
    </ThemeModeProvider>,
  );
  return login;
}

describe("login page", () => {
  it("starts blank without preset credential hints and includes theme control", () => {
    renderLogin();

    expect((screen.getByLabelText(/^Email/) as HTMLInputElement).value).toBe("");
    expect((screen.getByLabelText(/^Password/) as HTMLInputElement).value).toBe("");
    expect((screen.getByLabelText(/^Password/) as HTMLInputElement).type).toBe("password");
    expect(screen.queryByText(/admin@nik\.ai/i)).toBeNull();
    expect(screen.queryByText(/preset password|demo password|default credentials/i)).toBeNull();
    expect(screen.getByRole("button", { name: "Switch to dark mode" })).toBeTruthy();
  });

  it("submits credentials entered by the user", async () => {
    const login = renderLogin();
    fireEvent.change(screen.getByLabelText(/^Email/), {
      target: { value: "person@example.com" },
    });
    fireEvent.change(screen.getByLabelText(/^Password/), {
      target: { value: "user-entered-password" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Sign In" }));

    await waitFor(() => {
      expect(login).toHaveBeenCalledWith(
        "person@example.com",
        "user-entered-password",
      );
    });
  });
});