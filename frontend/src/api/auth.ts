import client from "./client";
import {
  AuthResponse,
  ResendOtpResponse,
  SignupResponse,
  User,
  VerifyOtpResponse,
} from "@/types";

export interface SignupPayload {
  first_name: string;
  last_name: string;
  email: string;
  password: string;
  mobile?: string;
}

export const authApi = {
  signup: async (
    payload: SignupPayload,
  ): Promise<SignupResponse> => {
    const { data } =
      await client.post<SignupResponse>(
        "/auth/signup",
        payload,
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

  /*
   * Six-digit email verification.
   *
   * These are public auth endpoints: the account has no session until
   * the code is confirmed.
   */
  verifyOtp: async (
    email: string,
    code: string,
  ): Promise<VerifyOtpResponse> => {
    const { data } =
      await client.post<VerifyOtpResponse>(
        "/auth/verify-otp",
        { email, code },
      );

    return data;
  },

  resendOtp: async (
    email: string,
  ): Promise<ResendOtpResponse> => {
    const { data } =
      await client.post<ResendOtpResponse>(
        "/auth/resend-otp",
        { email },
      );

    return data;
  },

  /**
   * @deprecated The product now sends six-digit codes. Kept as a thin
   * alias for older clients; the backend routes it to resendOtp.
   */
  resendVerification: async (
    email: string,
  ) => authApi.resendOtp(email),

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
