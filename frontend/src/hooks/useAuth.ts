"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";

import { authApi } from "@/api/auth";
import { workspacesApi } from "@/api/workspaces";
import { useAppStore } from "@/store/useAppStore";
import { consumePostLoginPath, getErrorMessage, rememberPostLoginPath } from "@/api/client";

function isEmailVerificationRequired(error: unknown): boolean {
  const detail = (
    error as {
      response?: { data?: { detail?: unknown } };
    }
  )?.response?.data?.detail;

  return Boolean(
    detail &&
      typeof detail === "object" &&
      (detail as { code?: unknown }).code ===
        "EMAIL_VERIFICATION_REQUIRED",
  );
}

export function useAuth() {
  const router = useRouter();
  const queryClient = useQueryClient();

  const {
    setAuth,
    logout: storeLogout,
    isAuthenticated,
    user,
    updateUser,
    setActiveWorkspace,
  } = useAppStore();

  /*
   * ============================================================
   * CURRENT USER
   * ============================================================
   */

  useQuery({
    queryKey: ["me"],
    queryFn: async () => {
      const data = await authApi.getMe();

      updateUser(data);

      return data;
    },
    enabled: isAuthenticated,
    staleTime: 0,
    refetchOnMount: true,
    refetchOnWindowFocus: true,
  });

  /*
   * ============================================================
   * SIGN UP
   * ============================================================
   *
   * Backend behavior:
   *
   * If email verification is enabled:
   *
   *   requires_email_verification === true
   *
   * The backend does NOT create an authenticated session yet.
   *
   * Therefore:
   *
   *   signup
   *      ↓
   *   verify email
   *      ↓
   *   login
   *      ↓
   *   workspace onboarding
   *
   * If verification is disabled and the backend gives us a
   * session, we can continue directly into authentication.
   */

  const signupMutation = useMutation({
    mutationFn: ({
      firstName,
      lastName,
      email,
      password,
      mobile,
    }: {
      firstName: string;
      lastName: string;
      email: string;
      password: string;
      mobile?: string;
    }) =>
      authApi.signup({
        first_name: firstName,
        last_name: lastName,
        email,
        password,
        mobile: mobile?.trim() || undefined,
      }),

    onSuccess: async (result) => {
      /*
       * Normal production path.
       *
       * The backend returns:
       *
       * requires_email_verification: true
       *
       * and sends a six-digit code. There is deliberately no session
       * until that code is confirmed.
       */
      if (result.requires_email_verification) {
        toast.success(
          result.verification_email_sent === false
            ? "Account created. Request a new code on the next screen."
            : "Account created. Enter the six-digit code we emailed you."
        );

        /*
         * Preserve the email so the verification screen can:
         *
         * - show the correct address
         * - resend a code without making the user type it
         */
        router.push(
          `/verify-email?email=${encodeURIComponent(result.email || "")}`
        );

        return;
      }

      /*
       * Development / email-verification-disabled path.
       *
       * If signup immediately authenticated the user, establish the
       * local auth state and continue to workspace onboarding.
       */
      try {
        const userProfile = await authApi.getMe();

        setAuth(userProfile);

        toast.success("Account created successfully.");

        await routeAfterAuth();
      } catch (error) {
        toast.error(
          getErrorMessage(
            error,
            "Your account was created, but we couldn't start your session."
          )
        );

        router.push("/login");
      }
    },

    onError: (error: unknown) => {
      toast.error(
        getErrorMessage(error, "Signup failed. Please try again.")
      );
    },
  });

  /*
   * ============================================================
   * LOGIN
   * ============================================================
   *
   * Login is the point where we decide whether the user needs:
   *
   *   /workspace
   *
   * or:
   *
   *   /dashboard
   *
   * based on their existing workspaces.
   */

  const loginMutation = useMutation({
    mutationFn: ({
      email,
      password,
    }: {
      email: string;
      password: string;
    }) => authApi.login(email, password),

    onSuccess: async () => {
      try {
        /*
         * Authentication cookies are already set by the backend.
         *
         * We only fetch the profile to populate the client store.
         */
        const userProfile = await authApi.getMe();

        setAuth(userProfile);

        toast.success("Welcome back!");

        await routeAfterAuth();
      } catch (error) {
        console.error("Post-login routing error:", error);

        toast.error(
          getErrorMessage(
            error,
            "We couldn't finish signing you in. Please try again."
          )
        );
      }
    },

    onError: (
      error: unknown,
      variables: { email: string; password: string },
    ) => {
      console.error("Login error:", error);

      if (isEmailVerificationRequired(error)) {
        toast.error(
          "Verify your email with the six-digit code before signing in."
        );

        router.push(
          `/verify-email?email=${encodeURIComponent(variables.email)}`
        );

        return;
      }

      toast.error(
        getErrorMessage(
          error,
          "Invalid email or password."
        )
      );
    },
  });

  /*
   * ============================================================
   * ROUTE AFTER AUTHENTICATION
   * ============================================================
   *
   * This is the important part of the onboarding flow.
   *
   * Authenticated user
   *        ↓
   * GET /workspaces
   *        ↓
   * ┌───────────────────────────────┐
   * │ No workspaces                 │
   * │ → /workspace                  │
   * └───────────────────────────────┘
   *
   * OR
   *
   * ┌───────────────────────────────┐
   * │ Existing workspace            │
   * │ → /dashboard                  │
   * └───────────────────────────────┘
   */

  async function routeAfterAuth() {
    try {
      const workspaces = await workspacesApi.list();

      /*
       * BRAND NEW USER
       *
       * The account exists, but no workspace has been created yet.
       *
       * This is the exact point where Personal vs Business
       * onboarding should appear.
       */
      if (!workspaces || workspaces.length === 0) {
        setActiveWorkspace(null);

        window.location.replace("/workspace");

        return;
      }

      /*
       * EXISTING USER
       *
       * Restore their last selected workspace where possible.
       */
      const storedId =
        typeof window !== "undefined"
          ? localStorage.getItem("active_workspace_id")
          : null;

      const selected =
        (storedId
          ? workspaces.find((workspace) => workspace.id === storedId)
          : null) ||
        workspaces[0];

      if (!selected) {
        /*
         * Defensive fallback.
         *
         * This should only be reached if the API returned an
         * unexpected empty/invalid response.
         */
        window.location.replace("/workspace");

        return;
      }

      setActiveWorkspace(selected);

      // A session timeout should return to the exact protected screen, including filters/query params.
      // New users still go through workspace onboarding above.
      const returnTo = consumePostLoginPath();
      if (returnTo) {
        window.location.replace(returnTo);
        return;
      }

      /*
       * Full browser navigation is intentional.
       *
       * The backend uses httpOnly authentication cookies and the
       * frontend middleware protects /dashboard.
       *
       * A hard navigation guarantees the newly authenticated
       * session is evaluated correctly by the protected route.
       */
      window.location.replace("/dashboard");
    } catch (error) {
      /*
       * IMPORTANT:
       *
       * An API failure is NOT the same as "no workspace".
       *
       * Never send an existing user into workspace creation just
       * because GET /workspaces temporarily failed.
       */
      console.error("Workspace lookup failed:", error);

      toast.error(
        getErrorMessage(
          error,
          "We couldn't load your workspaces. Please try again."
        )
      );
    }
  }

  /*
   * ============================================================
   * LOGOUT
   * ============================================================
   */

  const logoutMutation = useMutation({
    mutationFn: () => {
      rememberPostLoginPath();
      return authApi.logout();
    },

    onSuccess: () => {
      storeLogout();

      queryClient.clear();

      router.push("/login");
    },
    onError: (error) => {
      toast.error(
        getErrorMessage(error, "We couldn't safely end your session. Please try again."),
      );
    },
  });

  return {
    user,
    isAuthenticated,

    signup: signupMutation.mutate,
    isSigningUp: signupMutation.isPending,

    login: loginMutation.mutate,
    isLoggingIn: loginMutation.isPending,

    logout: logoutMutation.mutate,
  };
}
