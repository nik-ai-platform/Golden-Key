import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ForgotEmailPage } from "../../src/pages/ForgotEmailPage";
import { ForgotPasswordPage } from "../../src/pages/ForgotPasswordPage";
import { ResetPasswordPage } from "../../src/pages/ResetPasswordPage";
import { ProductProfilePage } from "../../src/pages/ProductProfilePage";
import { ThemeModeProvider } from "../../src/theme/ThemeModeProvider";
import * as authService from "../../src/services/authService";
import * as productApi from "../../src/services/productApi";

vi.mock("../../src/services/authService", () => ({
  forgotPassword: vi.fn(),
  resetPassword: vi.fn(),
  forgotEmail: vi.fn(),
  verifyForgotEmail: vi.fn(),
  setRecoveryEmail: vi.fn(),
  verifyRecoveryEmail: vi.fn(),
}));

vi.mock("../../src/services/productApi", () => ({
  getProfile: vi.fn(),
}));

vi.mock("../../src/hooks/useAuth", () => ({
  useAuth: () => ({ logout: vi.fn() }),
}));

function renderPage(page: ReactNode, route = "/") {
  render(
    <ThemeModeProvider>
      <MemoryRouter initialEntries={[route]}>{page}</MemoryRouter>
    </ThemeModeProvider>,
  );
}

function renderProfile() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={queryClient}>
      <ThemeModeProvider>
        <MemoryRouter><ProductProfilePage /></MemoryRouter>
      </ThemeModeProvider>
    </QueryClientProvider>,
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

  it("requests a forgot-email code with a generic confirmation", async () => {
    vi.mocked(authService.forgotEmail).mockResolvedValue({
      message: "If a verified recovery account matches that address, a recovery code has been sent.",
    });
    renderPage(<ForgotEmailPage />, "/forgot-email");

    fireEvent.change(screen.getByLabelText(/^Recovery email/), {
      target: { value: "secondary@example.com" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send recovery code" }));

    await waitFor(() => expect(authService.forgotEmail).toHaveBeenCalledWith("secondary@example.com"));
    expect(await screen.findByText(/If a verified recovery account matches/i)).toBeTruthy();
    expect(screen.getByLabelText(/^Recovery code/)).toBeTruthy();
  });

  it("verifies a code and shows only the masked sign-in email", async () => {
    vi.mocked(authService.forgotEmail).mockResolvedValue({ message: "Generic response" });
    vi.mocked(authService.verifyForgotEmail).mockResolvedValue({ email: "n******@gmail.com" });
    renderPage(<ForgotEmailPage />, "/forgot-email");

    fireEvent.change(screen.getByLabelText(/^Recovery email/), {
      target: { value: "secondary@example.com" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Send recovery code" }));
    fireEvent.change(await screen.findByLabelText(/^Recovery code/), {
      target: { value: "123456" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Verify code" }));

    expect(await screen.findByText("Account found")).toBeTruthy();
    expect(screen.getByText("n******@gmail.com")).toBeTruthy();
    expect(authService.verifyForgotEmail).toHaveBeenCalledWith({
      recovery_email: "secondary@example.com",
      code: "123456",
    });
  });

  it("keeps support fallback and theme control", () => {
    renderPage(<ForgotEmailPage />, "/forgot-email");

    expect(screen.getByText(/Can't access your recovery email/i)).toBeTruthy();
    expect(screen.getByRole("link", { name: /Contact support/ }).getAttribute("href")).toBe(
      "mailto:support@nik-ai-platform.com",
    );
    expect(screen.getByRole("button", { name: "Switch to dark mode" })).toBeTruthy();
  });

  it("configures and verifies a recovery email from Profile", async () => {
    vi.mocked(productApi.getProfile).mockResolvedValue({
      id: 1,
      username: "customer",
      email: "customer@example.com",
      premium: false,
      recovery_email_masked: "s********@example.com",
      recovery_email_verified: false,
    });
    vi.mocked(authService.setRecoveryEmail).mockResolvedValue({
      message: "Recovery email verification code sent",
    });
    vi.mocked(authService.verifyRecoveryEmail).mockResolvedValue({
      message: "Recovery email verified",
    });
    renderProfile();

    expect(await screen.findByText("Account Recovery")).toBeTruthy();
    expect(screen.getByText("Not verified")).toBeTruthy();
    fireEvent.change(screen.getByLabelText(/^Recovery email/), {
      target: { value: "secondary@example.com" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Update recovery email" }));
    expect(await screen.findByLabelText(/^Verification code/)).toBeTruthy();
    fireEvent.change(screen.getByLabelText(/^Verification code/), {
      target: { value: "123456" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Verify" }));

    await waitFor(() => expect(authService.verifyRecoveryEmail).toHaveBeenCalledWith("123456"));
  });

  it("shows a verified recovery status in Profile", async () => {
    vi.mocked(productApi.getProfile).mockResolvedValue({
      id: 1,
      username: "customer",
      email: "customer@example.com",
      premium: false,
      recovery_email_masked: "s********@example.com",
      recovery_email_verified: true,
    });
    renderProfile();

    expect(await screen.findByText("Verified")).toBeTruthy();
    expect(screen.getByText("s********@example.com")).toBeTruthy();
  });
});