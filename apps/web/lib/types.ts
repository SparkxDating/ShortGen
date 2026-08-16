export type User = {
  id: string;
  email: string;
  name: string;
  avatar_url: string | null;
};

export type Workspace = {
  id: string;
  name: string;
  slug: string;
  owner_id: string;
  role: string;
};

export type Project = {
  id: string;
  workspace_id: string;
  name: string;
  description: string | null;
  created_by: string;
  created_at: string;
  updated_at: string | null;
};

export type Job = {
  id: string;
  workspace_id: string;
  video_id: string;
  job_type: string;
  status: "QUEUED" | "RUNNING" | "COMPLETED" | "FAILED" | "CANCELLED" | string;
  progress: number;
  current_stage: string;
  error_message: string | null;
  retry_count: number;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
};

export type Member = {
  id: string;
  user_id: string;
  email: string;
  name: string;
  role: string;
  created_at: string;
};

export type Invite = {
  id: string;
  workspace_id: string;
  email: string;
  role: string;
  status: string;
  token: string;
  invited_by: string;
  expires_at: string;
  created_at: string;
};

export type Asset = {
  id: string;
  workspace_id: string;
  name: string;
  kind: string;
  object_key: string;
  public_url: string;
  content_type: string;
  size_bytes: number;
  original_filename: string;
  created_by: string;
  created_at: string;
};

export type Template = {
  id: string;
  workspace_id: string | null;
  name: string;
  description: string | null;
  is_system: boolean;
  config: Record<string, unknown>;
  created_by: string | null;
  created_at: string;
};

export type Plan = {
  id: string;
  slug: string;
  name: string;
  description: string;
  monthly_credits: number;
  price_cents: number;
  currency: string;
};

export type CreditPack = {
  id: string;
  slug: string;
  name: string;
  credits: number;
  price_cents: number;
  currency: string;
};

export type Usage = {
  workspace_id: string;
  balance: number;
  reserved: number;
  available: number;
  plan: Plan | null;
  subscription_status: string;
  videos_this_period: number;
  credits_spent_this_period: number;
  estimated_next_video: number;
};

export type LedgerEntry = {
  id: string;
  amount: number;
  balance_after: number;
  entry_type: string;
  description: string;
  created_at: string;
};

export type Video = {
  id: string;
  workspace_id: string;
  project_id: string;
  title: string;
  status: string;
  progress: number;
  duration: number | null;
  aspect_ratio: string;
  resolution: string;
  thumbnail_url: string | null;
  video_url: string | null;
  created_by: string;
  created_at: string;
  updated_at: string | null;
  latest_job: Job | null;
};
