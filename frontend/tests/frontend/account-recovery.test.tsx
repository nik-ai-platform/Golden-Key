import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ForgotEmailPage } from "../../src/pages/ForgotEmailPage";
import { ForgotPasswordPage } from "../../src/pages/ForgotPasswordPage";
import { ResetPasswordPage } from "../../src/pages/ResetPasswordPage";
import { ThemeModeProvider } from "../../src/theme/ThemeModeProvider";
import * as authService from "../../src/services/authService";

vi.mock("../../src/services/authService", () => ({
  forgotPassword: vi.fn(),
  resetPassword: vi.fn(),
}));

function renderPage(page: ReactNode, route = "/") {
  render(
    <ThemeModeProvider>
      <MemoryRouter initialEntries={[route]}>{page}</MemoryRouter>
    </ThemeModeProvider>,
  );
}

describe("account recovery", () => {
  beforeEach(() => vi.clearAllMocks());

  it("submits forgot password and shows the generic confirmation", async () => {
    vi.mocked(authService.forgotPassword).mockResolvedValue({
      message: "If an account exists for that email, password reset instructions have been sent.",
    });
    renderPage(<ForgotPasswordPage />, "/forgot-password");

    fireEvent.change(screen.getByLabelText(/^Email/), {
      target: { value: "customer@example.com" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send reset instructions" }));

    await waitFor(() => expect(authService.forgotPassword).toHaveBeenCalledWith("customer@example.com"));
    expect(await screen.findByText(/If an account exists for that email/i)).toBeTruthy();
  });

  it("validates matching passwords before reset", async () => {
    renderPage(<ResetPasswordPage />, "/reset-password?token=opaque-token");
    fireEvent.change(screen.getByLabelText(/^New password/), { target: { value: "password-one" } });
    fireEvent.change(screen.getByLabelText(/^Confirm password/), { target: { value: "password-two" } });
    fireEvent.click(screen.getByRole("button", { name: "Update password" }));

    expect(await screen.findByText("Passwords must match.")).toBeTruthy();
    expect(authService.resetPassword).not.toHaveBeenCalled();
  });

  it("shows a successful reset state", async () => {
    vi.mocked(authService.resetPassword).mockResolvedValue({ message: "Password updated" });
    renderPage(<ResetPasswordPage />, "/reset-password?token=opaque-token");
    fireEvent.change(screen.getByLabelText(/^New password/), { target: { value: "new-password" } });
    fireEvent.change(screen.getByLabelText(/^Confirm password/), { target: { value: "new-password" } });
    fireEvent.click(screen.getByRole("button", { name: "Update password" }));

    expect(await screen.findByText("Your password has been reset successfully.")).toBeTruthy();
    expect(authService.resetPassword).toHaveBeenCalledWith({
      token: "opaque-token",
      new_password: "new-password",
    });
  });

  it("uses support-only email recovery with theme control", () => {
    renderPage(<ForgotEmailPage />, "/forgot-email");

    expect(screen.getByText(/contact support for account recovery/i)).toBeTruthy();
    expect(screen.getByRole("link", { name: "Contact support" }).getAttribute("href")).toBe(
      "mailto:support@nik-ai-platform.com",
    );
    expect(screen.getByRole("button", { name: "Switch to dark mode" })).toBeTruthy();
  });
});