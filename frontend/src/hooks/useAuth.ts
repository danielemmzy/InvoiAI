"use client";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";
import { authApi } from "@/api/auth";
import { useAppStore } from "@/store/useAppStore";

export function useAuth() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { setAuth, logout: storeLogout, isAuthenticated, user, updateUser } = useAppStore();

  // Fetch current user — runs when authenticated
  useQuery({
    queryKey: ["me"],
    queryFn: async () => {
      const data = await authApi.getMe();
      updateUser(data); // update store directly
      return data;
    },
    enabled: isAuthenticated,
    staleTime: 5 * 60 * 1000,
  });

  // Signup
  const signupMutation = useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      authApi.signup(email, password),
    onSuccess: async (data) => {
      if (!data.access_token) {
        toast.success("Account created! Check your email to verify.");
        router.push("/login");
        return;
      }
      const userProfile = await authApi.getMe();
      setAuth(userProfile, data.access_token, data.refresh_token);
      toast.success("Welcome to InvoiAI!");
      router.push("/dashboard");
    },
    onError: (error: unknown) => {
      toast.error(getErrorMessage(error) || "Signup failed.");
    },
  });

  // Login
  const loginMutation = useMutation({
  mutationFn: ({ email, password }: { email: string; password: string }) =>
    authApi.login(email, password),

  onSuccess: async (data) => {
    // Save tokens FIRST
    localStorage.setItem("access_token", data.access_token);
    localStorage.setItem("refresh_token", data.refresh_token);

    // Now get profile
    const userProfile = await authApi.getMe();

    setAuth(
      userProfile,
      data.access_token,
      data.refresh_token
    );

    toast.success("Welcome back!");
    router.push("/dashboard");
  },

  onError: (error: any) => {
    console.error(error);
    toast.error(
      error?.response?.data?.detail ||
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

  // Google connect
  const connectGoogleMutation = useMutation({
    mutationFn: authApi.getGoogleConnectUrl,
    onSuccess: ({ auth_url }) => {
      window.open(auth_url, "_blank");
    },
    onError: () => toast.error("Could not connect Google."),
  });

  return {
    user,
    isAuthenticated,
    signup: signupMutation.mutate,
    isSigningUp: signupMutation.isPending,
    login: loginMutation.mutate,
    isLoggingIn: loginMutation.isPending,
    logout: logoutMutation.mutate,
    connectGoogle: connectGoogleMutation.mutate,
    isConnectingGoogle: connectGoogleMutation.isPending,
  };
}

function getErrorMessage(error: unknown): string {
  if (error && typeof error === "object" && "response" in error) {
    const e = error as { response?: { data?: { detail?: string } } };
    return e.response?.data?.detail || "";
  }
  return "";
}