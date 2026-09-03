import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { getApiErrorMessage } from "../../src/api/client";
import { RegisterPage } from "../../src/pages/RegisterPage";
import { ThemeModeProvider } from "../../src/theme/ThemeModeProvider";
import * as authService from "../../src/services/authService";

vi.mock("../../src/services/authService", () => ({
  register: vi.fn(),
}));

vi.mock("../../src/hooks/useAuth", () => ({
  useAuth: () => ({ isAuthenticated: false }),
}));

function renderRegistration() {
  render(
    <ThemeModeProvider>
      <MemoryRouter initialEntries={["/register"]}>
        <Routes>
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/login" element={<div>Sign in destination</div>} />
        </Routes>
      </MemoryRouter>
    </ThemeModeProvider>,
  );
}

function submitRegistration() {
  fireEvent.change(screen.getByLabelText(/^Username/), {
    target: { value: "new_customer" },
  });
  fireEvent.change(screen.getByLabelText(/^Email/), {
    target: { value: "new.customer@example.com" },
  });
  fireEvent.change(screen.getByLabelText(/^Password/), {
    target: { value: "correct-horse-battery-staple" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Create account" }));
}

describe("registration", () => {
  beforeEach(() => vi.clearAllMocks());

  it("submits all fields and redirects after successful registration", async () => {
    vi.mocked(authService.register).mockResolvedValue(undefined);
    renderRegistration();

    submitRegistration();

    await waitFor(() => {
      expect(authService.register).toHaveBeenCalledWith({
        username: "new_customer",
        email: "new.customer@example.com",
        password: "correct-horse-battery-staple",
      });
    });
    expect(await screen.findByText("Sign in destination")).toBeTruthy();
  });

  it.each([
    "Email already registered",
    "Username already registered",
  ])("shows the API message: %s", async (message) => {
    vi.mocked(authService.register).mockRejectedValue({ status: 400, message });
    renderRegistration();

    submitRegistration();

    expect(await screen.findByText(message)).toBeTruthy();
  });

  it("shows a readable FastAPI validation message", async () => {
    const message = getApiErrorMessage(
      {
        detail: [
          { loc: ["body", "email"], msg: "Field required", type: "missing" },
          { loc: ["body", "password"], msg: "Password is too short", type: "value_error" },
        ],
      },
      422,
    );
    vi.mocked(authService.register).mockRejectedValue({ status: 422, message });
    renderRegistration();

    submitRegistration();

    expect(await screen.findByText("Field required. Password is too short")).toBeTruthy();
  });

  it("uses the generic fallback for an unknown error", async () => {
    vi.mocked(authService.register).mockRejectedValue(null);
    renderRegistration();

    submitRegistration();

    expect(await screen.findByText("Registration failed. Please try again.")).toBeTruthy();
  });
});