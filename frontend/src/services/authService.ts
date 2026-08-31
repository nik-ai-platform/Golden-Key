import { client } from "../api/client";
import type {
  AccessTokenResponse,
  AuthUser,
  ForgotEmailVerifyRequest,
  LoginRequest,
  MessageResponse,
  MaskedEmailResponse,
  RegisterRequest,
  ResetPasswordRequest,
} from "../types/auth";

export async function login(payload: LoginRequest): Promise<AccessTokenResponse> {
  const { data } = await client.post<AccessTokenResponse>("/auth/login", payload);
  return data;
}

export async function register(payload: RegisterRequest): Promise<void> {
  await client.post("/auth/register", payload);
}

export async function forgotPassword(email: string): Promise<MessageResponse> {
  const { data } = await client.post<MessageResponse>("/auth/forgot-password", { email });
  return data;
}

export async function resetPassword(payload: ResetPasswordRequest): Promise<MessageResponse> {
  const { data } = await client.post<MessageResponse>("/auth/reset-password", payload);
  return data;
}

export async function setRecoveryEmail(recoveryEmail: string): Promise<MessageResponse> {
  const { data } = await client.post<MessageResponse>("/auth/recovery-email", {
    recovery_email: recoveryEmail,
  });
  return data;
}

export async function verifyRecoveryEmail(code: string): Promise<MessageResponse> {
  const { data } = await client.post<MessageResponse>("/auth/recovery-email/verify", { code });
  return data;
}

export async function forgotEmail(recoveryEmail: string): Promise<MessageResponse> {
  const { data } = await client.post<MessageResponse>("/auth/forgot-email", {
    recovery_email: recoveryEmail,
  });
  return data;
}

export async function verifyForgotEmail(
  payload: ForgotEmailVerifyRequest,
): Promise<MaskedEmailResponse> {
  const { data } = await client.post<MaskedEmailResponse>("/auth/forgot-email/verify", payload);
  return data;
}

export async function getCurrentUser(): Promise<AuthUser> {
  const { data } = await client.get<Partial<AuthUser> & Pick<AuthUser, "id" | "username" | "email">>("/users/me");
  return {
    ...data,
    role: data.role ?? "user",
    is_active: data.is_active ?? true,
  };
}
