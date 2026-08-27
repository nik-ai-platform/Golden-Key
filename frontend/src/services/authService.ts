import { client } from "../api/client";
import type { AccessTokenResponse, AuthUser, LoginRequest, RegisterRequest } from "../types/auth";

export async function login(payload: LoginRequest): Promise<AccessTokenResponse> {
  const { data } = await client.post<AccessTokenResponse>("/auth/login", payload);
  return data;
}

export async function register(payload: RegisterRequest): Promise<void> {
  await client.post("/auth/register", payload);
}

export async function getCurrentUser(): Promise<AuthUser> {
  const { data } = await client.get<Partial<AuthUser> & Pick<AuthUser, "id" | "username" | "email">>("/users/me");
  return {
    ...data,
    role: data.role ?? "user",
    is_active: data.is_active ?? true,
  };
}
