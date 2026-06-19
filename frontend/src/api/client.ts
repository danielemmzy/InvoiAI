// ─────────────────────────────────────────────
// API Client — Axios instance
// Handles auth headers + token refresh automatically
// Like a Dio client in Flutter
// ─────────────────────────────────────────────

import axios, { AxiosInstance, AxiosError } from "axios";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const client: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: { "Content-Type": "application/json" },
});

// ── Request interceptor ───────────────────────────────────────────────────────
// Attaches the JWT token to every request automatically
// Equivalent to Flutter Dio interceptors
client.interceptors.request.use(
  (config) => {
    if (typeof window !== "undefined") {
      const token = localStorage.getItem("access_token");
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ── Response interceptor ──────────────────────────────────────────────────────
// Handles 401s — tries to refresh the token automatically
// If refresh fails, clears storage and redirects to login
client.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as typeof error.config & { _retry?: boolean };

    if (error.response?.status === 401 && !original?._retry) {
      original._retry = true;

      const refreshToken = localStorage.getItem("refresh_token");
      if (!refreshToken) {
        // No refresh token — clear and redirect to login
        clearAuthStorage();
        window.location.href = "/login";
        return Promise.reject(error);
      }

      try {
        const { data } = await axios.post(`${BASE_URL}/auth/refresh`, {
          refresh_token: refreshToken,
        });

        localStorage.setItem("access_token", data.access_token);
        localStorage.setItem("refresh_token", data.refresh_token);

        // Retry the original request with new token
        if (original?.headers) {
          original.headers.Authorization = `Bearer ${data.access_token}`;
        }
        return client(original!);
      } catch {
        // Refresh failed — force logout
        clearAuthStorage();
        window.location.href = "/login";
        return Promise.reject(error);
      }
    }

    return Promise.reject(error);
  }
);

export function clearAuthStorage() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");
  localStorage.removeItem("user");
}

export default client;