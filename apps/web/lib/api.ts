import type {
  Asset,
  CreditPack,
  Invite,
  Job,
  LedgerEntry,
  Member,
  Plan,
  Project,
  Template,
  Usage,
  User,
  Video,
  Workspace,
} from "@/lib/types";

const TOKEN_KEY = "mpt_saas_token";

export function getApiBase(): string {
  return process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null): void {
  if (typeof window === "undefined") return;
  if (token) window.localStorage.setItem(TOKEN_KEY, token);
  else window.localStorage.removeItem(TOKEN_KEY);
}

type ApiError = Error & { status?: number };

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body && !(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(`${getApiBase()}${path}`, {
    ...init,
    headers,
  });
  if (response.status === 204) return undefined as T;
  const data = await response.json().catch(() => ({}));
  if (response.status === 401 && typeof window !== "undefined") {
    setToken(null);
    if (!window.location.pathname.startsWith("/login") && !window.location.pathname.startsWith("/register")) {
      window.location.href = "/login";
    }
  }
  if (!response.ok) {
    const error: ApiError = new Error(
      typeof data.detail === "string" ? data.detail : "Request failed",
    );
    error.status = response.status;
    throw error;
  }
  return data as T;
}

export const api = {
  register: (payload: { email: string; password: string; name: string }) =>
    request<{ access_token: string; user: User }>("/api/v1/auth/register", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  login: (payload: { email: string; password: string }) =>
    request<{ access_token: string; user: User }>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  me: () => request<User>("/api/v1/auth/me"),
  workspaces: () => request<Workspace[]>("/api/v1/workspaces"),
  createWorkspace: (name: string) =>
    request<Workspace>("/api/v1/workspaces", {
      method: "POST",
      body: JSON.stringify({ name }),
    }),
  projects: (workspaceId?: string) =>
    request<Project[]>(
      workspaceId ? `/api/v1/projects?workspace_id=${workspaceId}` : "/api/v1/projects",
    ),
  project: (id: string) => request<Project>(`/api/v1/projects/${id}`),
  createProject: (payload: { workspace_id: string; name: string; description?: string }) =>
    request<Project>("/api/v1/projects", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  deleteProject: (id: string) =>
    request<void>(`/api/v1/projects/${id}`, { method: "DELETE" }),
  videos: (params?: { workspace_id?: string; project_id?: string }) => {
    const search = new URLSearchParams();
    if (params?.workspace_id) search.set("workspace_id", params.workspace_id);
    if (params?.project_id) search.set("project_id", params.project_id);
    const suffix = search.toString() ? `?${search}` : "";
    return request<Video[]>(`/api/v1/videos${suffix}`);
  },
  video: (id: string) => request<Video>(`/api/v1/videos/${id}`),
  createVideo: (payload: Record<string, unknown>) =>
    request<Video>("/api/v1/videos", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  job: (id: string) => request<Job>(`/api/v1/jobs/${id}`),
  cancelJob: (id: string) =>
    request<{ id: string; status: string }>(`/api/v1/jobs/${id}/cancel`, { method: "POST" }),
  retryJob: (id: string) => request<Job>(`/api/v1/jobs/${id}/retry`, { method: "POST" }),
  members: (workspaceId: string) => request<Member[]>(`/api/v1/workspaces/${workspaceId}/members`),
  updateMember: (workspaceId: string, userId: string, role: string) =>
    request<Member>(`/api/v1/workspaces/${workspaceId}/members/${userId}`, {
      method: "PATCH",
      body: JSON.stringify({ role }),
    }),
  removeMember: (workspaceId: string, userId: string) =>
    request<void>(`/api/v1/workspaces/${workspaceId}/members/${userId}`, { method: "DELETE" }),
  invites: (workspaceId: string) => request<Invite[]>(`/api/v1/workspaces/${workspaceId}/invites`),
  createInvite: (workspaceId: string, email: string, role: string) =>
    request<Invite>(`/api/v1/workspaces/${workspaceId}/invites`, {
      method: "POST",
      body: JSON.stringify({ email, role }),
    }),
  revokeInvite: (workspaceId: string, inviteId: string) =>
    request<void>(`/api/v1/workspaces/${workspaceId}/invites/${inviteId}`, { method: "DELETE" }),
  previewInvite: (token: string) =>
    request<{ workspace_name: string; email: string; role: string; status: string }>(
      `/api/v1/invites/${token}`,
    ),
  acceptInvite: (token: string) =>
    request<Member>("/api/v1/invites/accept", {
      method: "POST",
      body: JSON.stringify({ token }),
    }),
  assets: (workspaceId: string) => request<Asset[]>(`/api/v1/assets?workspace_id=${workspaceId}`),
  uploadAsset: async (workspaceId: string, file: File) => {
    const body = new FormData();
    body.append("workspace_id", workspaceId);
    body.append("file", file);
    const headers = new Headers();
    const token = getToken();
    if (token) headers.set("Authorization", `Bearer ${token}`);
    const response = await fetch(`${getApiBase()}/api/v1/assets`, { method: "POST", headers, body });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(typeof data.detail === "string" ? data.detail : "Upload failed");
    }
    return data as Asset;
  },
  deleteAsset: (id: string) => request<void>(`/api/v1/assets/${id}`, { method: "DELETE" }),
  templates: (workspaceId?: string) =>
    request<Template[]>(
      workspaceId ? `/api/v1/templates?workspace_id=${workspaceId}` : "/api/v1/templates",
    ),
  createTemplate: (payload: { workspace_id: string; name: string; description?: string; config: Record<string, unknown> }) =>
    request<Template>("/api/v1/templates", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  deleteTemplate: (id: string) => request<void>(`/api/v1/templates/${id}`, { method: "DELETE" }),
  previewScript: (payload: { workspace_id: string; topic: string; video_language: string }) =>
    request<{ script: string }>("/api/v1/scripts/preview", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  usage: (workspaceId: string) => request<Usage>(`/api/v1/billing/usage?workspace_id=${workspaceId}`),
  plans: () => request<Plan[]>("/api/v1/billing/plans"),
  packs: () => request<CreditPack[]>("/api/v1/billing/packs"),
  ledger: (workspaceId: string) =>
    request<LedgerEntry[]>(`/api/v1/billing/ledger?workspace_id=${workspaceId}`),
  estimate: (duration: number, resolution: string) =>
    request<{ credits: number }>(`/api/v1/billing/estimate?duration=${duration}&resolution=${resolution}`),
  checkout: (workspaceId: string, kind: "pack" | "plan", itemId: string) =>
    request<{
      provider: string;
      completed: boolean;
      checkout_url: string | null;
      session_id?: string | null;
      message: string;
    }>(
      "/api/v1/billing/checkout",
      {
        method: "POST",
        body: JSON.stringify({ workspace_id: workspaceId, kind, item_id: itemId }),
      },
    ),
};

export function resolveMediaUrl(url: string | null | undefined): string | null {
  if (!url) return null;
  if (url.startsWith("http://") || url.startsWith("https://")) return url;
  return `${getApiBase()}${url}`;
}
