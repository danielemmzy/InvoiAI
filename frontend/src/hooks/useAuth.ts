"use client";
// ============================================================
// SECURITY FIX (see SECURITY_FIXES_APPLIED.md item #2): login no
// longer writes access_token/refresh_token to localStorage before
// calling setAuth — there's nothing to write. The backend's Set-Cookie
// headers on POST /auth/login already put both tokens in httpOnly
// cookies as part of that same response; this hook just needs the
// user's profile to populate the store.
// ============================================================
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";
import { authApi } from "@/api/auth";
import { useAppStore } from "@/store/useAppStore";
import { workspacesApi } from "@/api/workspaces";

export function useAuth() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { setAuth, logout: storeLogout, isAuthenticated, user, updateUser, setActiveWorkspace } = useAppStore();

  // Fetch current user — runs when authenticated
  useQuery({
    queryKey: ["me"],
    queryFn: async () => {
      const data = await authApi.getMe();
      updateUser(data); // update store directly
      return data;
    },
    enabled: isAuthenticated,
    staleTime: 0,
    refetchOnMount: true,
    refetchOnWindowFocus: true,
  });

// Signup
const signupMutation = useMutation({
  mutationFn: ({ email, password }: { email: string; password: string }) =>
    authApi.signup(email, password),

  onSuccess: async () => {
    toast.success(
      "Account created! Check your email to verify, then sign in."
    );

    router.push("/login?verified=0");
  },

  onError: (error: unknown) => {
    toast.error(getErrorMessage(error) || "Signup failed.");
  },
});

  // Login
  const loginMutation = useMutation({
  mutationFn: ({ email, password }: { email: string; password: string }) =>
    authApi.login(email, password),

  onSuccess: async () => {
    // The access_token / refresh_token cookies are already set by the
    // backend as part of this same response (httpOnly, so this hook
    // never sees or handles the raw token values at all). Just load
    // the profile now that the browser is authenticated.
    const userProfile = await authApi.getMe();
    setAuth(userProfile);

    toast.success("Welcome back!");
    await routeAfterAuth();
  },

  onError: (error: unknown) => {
    console.error(error);
    toast.error(
      getErrorMessage(error) ??
      "Invalid email or password."
    );
  },
});

  // Logout
  const logoutMutation = useMutation({
    mutationFn: authApi.logout,
    onSettled: () => {
      storeLogout();
      queryClient.clear();
      router.push("/login");
    },
  });

  async function routeAfterAuth() {
    try {
      const workspaces = await workspacesApi.list();
      const storedId = typeof window !== "undefined" ? localStorage.getItem("active_workspace_id") : null;
      const selected = (storedId && workspaces.find((w) => w.id === storedId)) || workspaces[0];
      if (!selected) {
        router.push("/workspace");
        return;
      }
      setActiveWorkspace(selected);

      // Force a real browser navigation after the BFF session and workspace
      // are established. This avoids a client-side navigation race where
      // Next can evaluate the protected route before the newly-set httpOnly
      // session cookie is visible to the route guard.
      window.location.replace("/dashboard");
    } catch (error) {
      // An API failure is not the same thing as "the user has no workspace".
      // Never send an existing user into workspace creation because the
      // workspace lookup temporarily failed.
      toast.error(getErrorMessage(error) || "We couldn't load your workspaces. Please try again.");
    }
  }

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

function getErrorMessage(error: unknown): string {
  if (error && typeof error === "object" && "response" in error) {
    const e = error as { response?: { data?: { detail?: string } } };
    return e.response?.data?.detail || "";
  }
  return "";
}
