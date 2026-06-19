// ─────────────────────────────────────────────
// Auth API — raw API calls for authentication
// Like a Repository class in Flutter BLoC
// ─────────────────────────────────────────────

import client from "./client";
import { AuthResponse, User } from "@/types";

export const authApi = {
  signup: async (email: string, password: string): Promise<AuthResponse> => {
    const { data } = await client.post<AuthResponse>("/auth/signup", {
      email,
      password,
    });
    return data;
  },

  login: async (email: string, password: string): Promise<AuthResponse> => {
    const { data } = await client.post<AuthResponse>("/auth/login", {
      email,
      password,
    });
    return data;
  },

  logout: async (): Promise<void> => {
    await client.post("/auth/logout");
  },

  getMe: async (): Promise<User> => {
    const { data } = await client.get<User>("/auth/me");
    return data;
  },

  refresh: async (refreshToken: string): Promise<AuthResponse> => {
    const { data } = await client.post<AuthResponse>("/auth/refresh", {
      refresh_token: refreshToken,
    });
    return data;
  },

  getGoogleConnectUrl: async (): Promise<{ auth_url: string }> => {
    const { data } = await client.get<{ auth_url: string }>("/auth/google/connect");
    return data;
  },

  getGoogleStatus: async (): Promise<{ google_connected: boolean }> => {
    const { data } = await client.get<{ google_connected: boolean }>("/auth/google/status");
    return data;
  },

  disconnectGoogle: async (): Promise<void> => {
    await client.delete("/auth/google/disconnect");
  },
};