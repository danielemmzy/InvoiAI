"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import { User } from "@/types";

interface AppState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  sidebarOpen: boolean;
  uploadProgress: number;

  setAuth: (
    user: User,
    accessToken: string,
    refreshToken: string
  ) => void;

  updateUser: (user: User) => void;

  logout: () => void;

  setSidebarOpen: (open: boolean) => void;
  setUploadProgress: (p: number) => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
      sidebarOpen: true,
      uploadProgress: 0,

      setAuth: (user, accessToken, refreshToken) => {
        if (typeof window !== "undefined") {
          localStorage.setItem("access_token", accessToken);
          localStorage.setItem("refresh_token", refreshToken);

          document.cookie = `access_token=${accessToken}; path=/; max-age=${
            7 * 24 * 60 * 60
          }`;
        }

        set({
          user,
          accessToken,
          refreshToken,
          isAuthenticated: !!accessToken,
        });
      },

      updateUser: (user) => set({ user }),

      logout: () => {
        if (typeof window !== "undefined") {
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
          localStorage.removeItem("invoiai-store");

          document.cookie =
            "access_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
        }

        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
        });
      },

      setSidebarOpen: (open) =>
        set({
          sidebarOpen: open,
        }),

      setUploadProgress: (uploadProgress) =>
        set({
          uploadProgress,
        }),
    }),
    {
      name: "invoiai-store",

      version: 2,

      migrate: (persistedState: any, version) => {
        if (version < 2) {
          return {
            user: null,
            accessToken: null,
            refreshToken: null,
            isAuthenticated: false,
          };
        }

        return persistedState;
      },

      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
      }),
    }
  )
);