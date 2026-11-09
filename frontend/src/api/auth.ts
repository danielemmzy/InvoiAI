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

export interface MfaFactor {
  id: string;
  friendly_name?: string | null;
  type: string;
  status: "verified" | "unverified";
  created_at: string;
}

export interface MfaFactorsResponse {
  factors: MfaFactor[];
  aal: "aal1" | "aal2";
  step_up_fresh: boolean;
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

  mfaFactors: async () =>
    (await client.get<MfaFactorsResponse>("/auth/mfa/factors")).data,

  mfaEnroll: async (friendly_name: string) =>
    (await client.post<{
      factor_id: string;
      friendly_name: string;
      qr_code: string | null;
      secret: string | null;
      uri: string | null;
    }>("/auth/mfa/enroll", { friendly_name })).data,

  mfaChallenge: async (factor_id: string) =>
    (await client.post<{ challenge_id: string; expires_at: number }>(
      "/auth/mfa/challenge", { factor_id },
    )).data,

  mfaVerify: async (factor_id: string, challenge_id: string, code: string) =>
    (await client.post<{ aal: "aal2"; recovery_codes: string[] | null }>(
      "/auth/mfa/verify", { factor_id, challenge_id, code },
    )).data,

  mfaRecovery: async (code: string) =>
    (await client.post<{ step_up_granted: boolean; expires_in_seconds: number }>(
      "/auth/mfa/recovery", { code },
    )).data,

  mfaRegenerateRecoveryCodes: async () =>
    (await client.post<{ recovery_codes: string[] }>(
      "/auth/mfa/recovery-codes/regenerate",
    )).data,

  mfaRemoveFactor: async (factor_id: string) =>
    (await client.delete<{ removed_factor_id: string }>(
      `/auth/mfa/factors/${encodeURIComponent(factor_id)}`,
    )).data,

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
