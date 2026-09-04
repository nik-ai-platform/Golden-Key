export type LoginRequest = {
  email: string;
  password: string;
};

export type RegisterRequest = {
  email: string;
  username: string;
  password: string;
};

export type MessageResponse = {
  message: string;
};

export type ResetPasswordRequest = {
  token: string;
  new_password: string;
};

export type ChangePasswordRequest = {
  current_password: string;
  new_password: string;
};

export type ForgotEmailVerifyRequest = {
  recovery_email: string;
  code: string;
};

export type MaskedEmailResponse = {
  email: string;
};

export type AccessTokenResponse = {
  access_token: string;
  token_type: "bearer";
};

export type AuthUser = {
  id: number;
  username: string;
  email: string;
  role: "user" | "admin" | "analyst" | "viewer";
  is_active: boolean;
  recovery_email_masked?: string | null;
  recovery_email_verified?: boolean;
};
