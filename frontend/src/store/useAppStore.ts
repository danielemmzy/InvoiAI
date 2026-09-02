"use client";

// ============================================================
// SECURITY FIX (see SECURITY_FIXES_APPLIED.md item #2):
// accessToken / refreshToken are gone from this store entirely — they
// never touch localStorage (directly or via zustand's persist) again.
// The backend's httpOnly cookies are the only place a session token
// lives now. This store only tracks who's logged in and which
// workspace is active, both of which are fine to persist since
// neither is a credential on its own.
// ============================================================

import { create } from "zustand";
import { persist } from "zustand/middleware";
import { User } from "@/types";
import type { WorkspaceSummary } from "@/types/workspace";

interface AppState {
  user: User | null;
  isAuthenticated: boolean;
  sidebarOpen: boolean;
  uploadProgress: number;
  activeWorkspace: WorkspaceSummary | null;

  setAuth: (user: User) => void;

  updateUser: (user: User) => void;

  logout: () => void;

  setSidebarOpen: (open: boolean) => void;
  setUploadProgress: (p: number) => void;
  setActiveWorkspace: (workspace: WorkspaceSummary | null) => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,
      sidebarOpen: true,
      uploadProgress: 0,
      activeWorkspace: null,

      setAuth: (user) => {
        set({
          user,
          isAuthenticated: true,
        });
      },

      updateUser: (user) => set({ user }),

      setActiveWorkspace: (workspace) => {
        if (typeof window !== "undefined") {
          if (workspace) {
            localStorage.setItem("active_workspace_id", workspace.id);
          } else {
            localStorage.removeItem("active_workspace_id");
          }
        }
        set({ activeWorkspace: workspace });
      },

      logout: () => {
        if (typeof window !== "undefined") {
          localStorage.removeItem("invoiai-store");
          localStorage.removeItem("active_workspace_id");
        }

        set({
          user: null,
          isAuthenticated: false,
          activeWorkspace: null,
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

      // Bumped from 2 -> 3: accessToken/refreshToken no longer exist on
      // this store's shape at all. Anyone rehydrating an old v2 payload
      // gets a clean logged-out state instead of a store with stray
      // token fields nothing reads anymore.
      version: 3,

      migrate: (persistedState: unknown, version) => {
        if (version < 3) {
          return {
            user: null,
            isAuthenticated: false,
            activeWorkspace: null,
          };
        }

        return persistedState;
      },

      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
        activeWorkspace: state.activeWorkspace,
      }),
    }
  )
);
