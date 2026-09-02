import client from "./client";
import {
  AuthResponse,
  SignupResponse,
  User,
} from "@/types";

export const authApi = {
  signup: async (
    email: string,
    password: string,
  ): Promise<SignupResponse> => {
    const { data } =
      await client.post<SignupResponse>(
        "/auth/signup",
        {
          email,
          password,
        },
      );

    return data;
  },

  login: async (
    email: string,
    password: string,
  ): Promise<AuthResponse> => {
    const { data } =
      await client.post<AuthResponse>(
        "/auth/login",
        {
          email,
          password,
        },
      );

    return data;
  },

  logout: async (): Promise<void> => {
    await client.post(
      "/auth/logout",
    );
  },

  getMe: async (): Promise<User> => {
    const { data } =
      await client.get<User>(
        "/auth/me",
      );

    return data;
  },

  forgotPassword: async (
    email: string,
  ) =>
    (
      await client.post(
        "/auth/forgot-password",
        { email },
      )
    ).data as {
      message: string;
    },

  resendVerification: async (
    email: string,
  ) =>
    (
      await client.post(
        "/auth/resend-verification",
        { email },
      )
    ).data as {
      message: string;
    },

  /*
   * Supabase password-reset token.
   *
   * This is a special one-time token and is allowed through the BFF
   * only for /auth/reset-password.
   *
   * It is never stored in localStorage or cookies.
   */
  resetPassword: async (
    password: string,
    recoveryToken?: string,
  ) =>
    (
      await client.post(
        "/auth/reset-password",
        { password },
        recoveryToken
          ? {
              headers: {
                Authorization:
                  `Bearer ${recoveryToken}`,
              },
            }
          : undefined,
      )
    ).data as {
      message: string;
    },
};