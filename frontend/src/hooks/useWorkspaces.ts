"use client";

import { useEffect } from "react";
import {
  useMutation,
  useQuery,
} from "@tanstack/react-query";

import toast from "react-hot-toast";

import { workspacesApi } from "@/api/workspaces";
import { useAppStore } from "@/store/useAppStore";
import { getErrorMessage } from "@/api/client";

import type {
  CompanySize,
  WorkspaceType,
} from "@/types/workspace";

export function useWorkspaces() {
  const activeWorkspace = useAppStore(
    (state) => state.activeWorkspace
  );

  const setActiveWorkspace = useAppStore(
    (state) => state.setActiveWorkspace
  );

  const query = useQuery({
    queryKey: ["workspaces"],
    queryFn: workspacesApi.list,

    staleTime: 30_000,

    retry: 2,
  });

  /*
   * Restore the previously selected workspace.
   */
  useEffect(() => {
    if (
      !query.data ||
      query.data.length === 0
    ) {
      return;
    }

    const activeStillExists =
      activeWorkspace &&
      query.data.some(
        (workspace) =>
          workspace.id === activeWorkspace.id
      );

    if (activeStillExists) {
      return;
    }

    const storedId =
      typeof window !== "undefined"
        ? localStorage.getItem(
            "active_workspace_id"
          )
        : null;

    const nextWorkspace =
      (storedId
        ? query.data.find(
            (workspace) =>
              workspace.id === storedId
          )
        : null) ||
      query.data[0];

    if (
      nextWorkspace &&
      nextWorkspace.id !== activeWorkspace?.id
    ) {
      setActiveWorkspace(nextWorkspace);
    }
  }, [
    query.data,
    activeWorkspace,
    setActiveWorkspace,
  ]);

  return query;
}

/*
 * ============================================================
 * CREATE WORKSPACE
 * ============================================================
 */

export function useCreateWorkspace() {
  const setActiveWorkspace = useAppStore(
    (state) => state.setActiveWorkspace
  );

  return useMutation({
    mutationFn: (input: {
      type: WorkspaceType;
      name?: string;
      currency?: string;
      country?: string;
      company_size?: CompanySize;
    }) => {
      return workspacesApi.create(input);
    },

    onSuccess: (workspace) => {
      /*
       * Immediately make the new workspace active.
       */
      setActiveWorkspace(workspace);

      /*
       * Tell the user the operation succeeded.
       */
      toast.success(
        workspace.type === "business"
          ? "Business workspace created."
          : "Personal workspace created."
      );

      /*
       * IMPORTANT:
       *
       * Use a full navigation rather than router.push().
       *
       * The dashboard is protected and the active workspace is
       * persisted by the Zustand store.
       *
       * A real browser navigation guarantees that the dashboard
       * starts from the newly-created workspace.
       */
      window.location.replace("/dashboard");
    },

    onError: (error) => {
      toast.error(
        getErrorMessage(
          error,
          "Workspace could not be created. Please try again."
        )
      );
    },
  });
}

/*
 * ============================================================
 * SWITCH WORKSPACE
 * ============================================================
 */

export function useSwitchWorkspace() {
  const setActiveWorkspace = useAppStore(
    (state) => state.setActiveWorkspace
  );

  return (
    workspace: Parameters<
      typeof setActiveWorkspace
    >[0]
  ) => {
    if (!workspace) {
      return;
    }

    setActiveWorkspace(workspace);

    window.location.replace("/dashboard");
  };
}