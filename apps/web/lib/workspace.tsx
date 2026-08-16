"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import type { Workspace } from "@/lib/types";

const KEY = "mpt_workspace_id";

type WorkspaceContextValue = {
  workspaces: Workspace[];
  workspace: Workspace | null;
  setWorkspaceId: (id: string) => void;
  refresh: () => Promise<void>;
};

const WorkspaceContext = createContext<WorkspaceContextValue | null>(null);

export function WorkspaceProvider({ children }: { children: React.ReactNode }) {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [workspaceId, setWorkspaceIdState] = useState("");

  async function refresh() {
    const items = await api.workspaces();
    setWorkspaces(items);
    const stored = typeof window !== "undefined" ? window.localStorage.getItem(KEY) : null;
    const next = items.find((item) => item.id === workspaceId)?.id
      || items.find((item) => item.id === stored)?.id
      || items[0]?.id
      || "";
    if (next && next !== workspaceId) {
      setWorkspaceIdState(next);
      window.localStorage.setItem(KEY, next);
    }
  }

  useEffect(() => {
    refresh().catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const value = useMemo<WorkspaceContextValue>(
    () => ({
      workspaces,
      workspace: workspaces.find((item) => item.id === workspaceId) || null,
      setWorkspaceId: (id: string) => {
        setWorkspaceIdState(id);
        window.localStorage.setItem(KEY, id);
      },
      refresh,
    }),
    [workspaces, workspaceId],
  );

  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}

export function useWorkspace() {
  const value = useContext(WorkspaceContext);
  if (!value) {
    throw new Error("useWorkspace must be used inside WorkspaceProvider");
  }
  return value;
}
