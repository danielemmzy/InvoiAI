"use client";

import { useEffect } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";
import { workspacesApi } from "@/api/workspaces";
import { useAppStore } from "@/store/useAppStore";
import { getErrorMessage } from "@/api/client";
import type { CompanySize, WorkspaceType } from "@/types/workspace";

export function useWorkspaces() {
  const activeWorkspace = useAppStore((s) => s.activeWorkspace);
  const setActiveWorkspace = useAppStore((s) => s.setActiveWorkspace);
  const query = useQuery({
    queryKey: ["workspaces"],
    queryFn: workspacesApi.list,
    staleTime: 30_000,
    retry: 2,
  });

  // Restore the last workspace, or safely fall back to the first membership.
  useEffect(() => {
    if (query.data && query.data.length && (!activeWorkspace || !query.data.some((w) => w.id === activeWorkspace.id))) {
      const storedId = typeof window !== "undefined" ? localStorage.getItem("active_workspace_id") : null;
      const next = (storedId && query.data.find((w) => w.id === storedId)) || query.data[0];
      if (next && next.id !== activeWorkspace?.id) setActiveWorkspace(next);
    }
  }, [query.data, activeWorkspace, setActiveWorkspace]);

  return query;
}

export function useCreateWorkspace() {
  const router = useRouter();
  const setActiveWorkspace = useAppStore((s) => s.setActiveWorkspace);
  return useMutation({
    mutationFn: (input: { type: WorkspaceType; name?: string; currency?: string; country?: string; company_size?: CompanySize }) => workspacesApi.create(input),
    onSuccess: (workspace) => {
      // Every AP/finance query key ends in the active workspace id (see
      // useAP.ts / useFinance.ts), so switching workspaces here just
      // points React Query at a different, empty set of cache entries.
      // No queryClient.clear() needed, and nothing from the previous
      // workspace is visible under the new one.
      setActiveWorkspace(workspace);
      toast.success(workspace.type === "business" ? "Business workspace created." : "Personal workspace created.");
      router.push("/dashboard");
    },
    onError: (error) => toast.error(getErrorMessage(error, "Workspace could not be created. Please try again.")),
  });
}

export function useSwitchWorkspace() {
  const router = useRouter();
  const setActiveWorkspace = useAppStore((s) => s.setActiveWorkspace);
  return (workspace: Parameters<typeof setActiveWorkspace>[0]) => {
    if (!workspace) return;
    setActiveWorkspace(workspace);
    router.push("/dashboard");
  };
}
