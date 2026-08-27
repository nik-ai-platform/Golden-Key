export type LoginRequest = {
  email: string;
  password: string;
};

export type RegisterRequest = {
  email: string;
  username: string;
  password: string;
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
};
