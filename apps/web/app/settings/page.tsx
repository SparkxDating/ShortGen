"use client";

import { FormEvent, useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api";
import type { Invite, Member } from "@/lib/types";
import { useWorkspace } from "@/lib/workspace";

function ProviderKeysCard() {
  const [llmProvider, setLlmProvider] = useState("moonshot");
  const [configured, setConfigured] = useState<Record<string, boolean>>({});
  const [values, setValues] = useState({
    kimi: "",
    openai: "",
    gemini: "",
    deepseek: "",
    pexels: "",
  });
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function load() {
    const result = await api.providerKeys();
    setLlmProvider(result.llm_provider || "moonshot");
    const next: Record<string, boolean> = {};
    for (const key of result.keys) next[key.id] = key.configured;
    setConfigured(next);
  }

  useEffect(() => {
    load().catch((err) => setError(err instanceof Error ? err.message : "Could not load keys"));
  }, []);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await api.saveProviderKeys({
        llm_provider: llmProvider,
        kimi: values.kimi.trim(),
        openai: values.openai.trim(),
        gemini: values.gemini.trim(),
        deepseek: values.deepseek.trim(),
        pexels: values.pexels.trim(),
      });
      setValues({ kimi: "", openai: "", gemini: "", deepseek: "", pexels: "" });
      await load();
      setMessage("Keys saved to config.toml. Blank fields were left unchanged.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save keys");
    } finally {
      setBusy(false);
    }
  }

  const fields = [
    { id: "kimi" as const, label: "Kimi / Moonshot", placeholder: "sk-..." },
    { id: "openai" as const, label: "OpenAI", placeholder: "sk-..." },
    { id: "gemini" as const, label: "Google Gemini", placeholder: "AIza..." },
    { id: "deepseek" as const, label: "DeepSeek", placeholder: "sk-..." },
    { id: "pexels" as const, label: "Pexels", placeholder: "Your Pexels API key" },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle>API keys</CardTitle>
        <CardDescription>
          Saved on this server in config.toml. The existing engine reads them. Leave a box empty to keep the current key.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form className="grid max-w-xl gap-4" onSubmit={save}>
          <div className="space-y-2">
            <Label htmlFor="llm_provider">Active script model</Label>
            <select
              id="llm_provider"
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
              value={llmProvider}
              onChange={(event) => setLlmProvider(event.target.value)}
            >
              <option value="moonshot">Kimi / Moonshot</option>
              <option value="openai">OpenAI</option>
              <option value="gemini">Google Gemini</option>
              <option value="deepseek">DeepSeek</option>
            </select>
          </div>
          {fields.map((field) => (
            <div key={field.id} className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor={field.id}>{field.label}</Label>
                <Badge tone={configured[field.id] ? "success" : "muted"}>
                  {configured[field.id] ? "saved" : "not set"}
                </Badge>
              </div>
              <Input
                id={field.id}
                type="password"
                autoComplete="off"
                placeholder={configured[field.id] ? "Saved. Paste a new key to replace it." : field.placeholder}
                value={values[field.id]}
                onChange={(event) => setValues((current) => ({ ...current, [field.id]: event.target.value }))}
              />
            </div>
          ))}
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
          {message ? <p className="text-sm text-muted-foreground">{message}</p> : null}
          <Button type="submit" disabled={busy}>
            {busy ? "Saving…" : "Save keys"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

function StripeCard() {
  const [status, setStatus] = useState<{
    provider: string;
    live_ready: boolean;
    secret_set: boolean;
    webhook_set: boolean;
    webhook_url: string;
    public_api_url: string;
    message: string;
  } | null>(null);
  const [secret, setSecret] = useState("");
  const [webhook, setWebhook] = useState("");
  const [enable, setEnable] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .stripeSettings()
      .then((next) => {
        setStatus(next);
        setEnable(next.provider === "stripe");
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load Stripe"));
  }, []);

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const next = await api.saveStripeSettings({
        secret_key: secret.trim(),
        webhook_secret: webhook.trim(),
        enable,
      });
      setStatus(next);
      setSecret("");
      setWebhook("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save Stripe");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Stripe billing</CardTitle>
        <CardDescription>
          Get keys from https://dashboard.stripe.com/apikeys. In Stripe → Developers → Webhooks, add the endpoint below as checkout.session.completed.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form className="grid max-w-xl gap-4" onSubmit={save}>
          <p className="text-sm text-muted-foreground">{status?.message}</p>
          {status?.webhook_url ? (
            <div className="space-y-1">
              <Label>Stripe webhook endpoint</Label>
              <p className="break-all rounded-md border bg-muted/40 px-3 py-2 text-xs">{status.webhook_url}</p>
            </div>
          ) : null}
          <div className="flex gap-2 text-xs">
            <Badge tone={status?.secret_set ? "success" : "muted"}>secret {status?.secret_set ? "saved" : "missing"}</Badge>
            <Badge tone={status?.webhook_set ? "success" : "muted"}>
              webhook {status?.webhook_set ? "saved" : "missing"}
            </Badge>
            <Badge tone={status?.live_ready ? "success" : "muted"}>{status?.provider || "local"}</Badge>
          </div>
          <div className="space-y-2">
            <Label htmlFor="stripe_secret">Secret key</Label>
            <Input
              id="stripe_secret"
              type="password"
              value={secret}
              onChange={(event) => setSecret(event.target.value)}
              placeholder={status?.secret_set ? "Saved. Paste to replace." : "sk_live_... or sk_test_..."}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="stripe_webhook">Webhook secret</Label>
            <Input
              id="stripe_webhook"
              type="password"
              value={webhook}
              onChange={(event) => setWebhook(event.target.value)}
              placeholder={status?.webhook_set ? "Saved. Paste to replace." : "whsec_..."}
            />
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={enable} onChange={(event) => setEnable(event.target.checked)} />
            Enable Stripe (credits only after a verified webhook)
          </label>
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
          <Button type="submit" disabled={busy}>
            {busy ? "Saving…" : "Save Stripe"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

function SocialCard() {
  const [status, setStatus] = useState<{
    configured: boolean;
    enabled: boolean;
    username_set: boolean;
    platforms: string[];
    message: string;
  } | null>(null);
  const [apiKey, setApiKey] = useState("");
  const [username, setUsername] = useState("");
  const [enabled, setEnabled] = useState(false);
  const [platforms, setPlatforms] = useState<string[]>(["tiktok", "instagram", "youtube"]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .socialSettings()
      .then((next) => {
        setStatus(next);
        setEnabled(next.enabled);
        if (next.platforms.length) setPlatforms(next.platforms);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load social"));
  }, []);

  function toggle(name: string) {
    setPlatforms((current) => (current.includes(name) ? current.filter((item) => item !== name) : [...current, name]));
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const next = await api.saveSocialSettings({
        api_key: apiKey.trim(),
        username: username.trim(),
        enabled,
        platforms,
      });
      setStatus(next);
      setApiKey("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save social");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Post to TikTok, Instagram, YouTube</CardTitle>
        <CardDescription>
          Uses the existing Upload-Post integration. Create a key at https://upload-post.com and connect those accounts there first.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form className="grid max-w-xl gap-4" onSubmit={save}>
          <p className="text-sm text-muted-foreground">{status?.message}</p>
          <Badge tone={status?.configured ? "success" : "muted"}>{status?.configured ? "ready" : "not configured"}</Badge>
          <div className="space-y-2">
            <Label htmlFor="upload_post_key">Upload-Post API key</Label>
            <Input
              id="upload_post_key"
              type="password"
              value={apiKey}
              onChange={(event) => setApiKey(event.target.value)}
              placeholder="Paste API key"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="upload_post_user">Upload-Post username</Label>
            <Input
              id="upload_post_user"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              placeholder="The profile you connected on Upload-Post"
            />
          </div>
          <div className="flex flex-wrap gap-4 text-sm">
            {["tiktok", "instagram", "youtube"].map((name) => (
              <label key={name} className="flex items-center gap-2 capitalize">
                <input type="checkbox" checked={platforms.includes(name)} onChange={() => toggle(name)} />
                {name}
              </label>
            ))}
          </div>
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={enabled} onChange={(event) => setEnabled(event.target.checked)} />
            Enable publishing
          </label>
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
          <Button type="submit" disabled={busy}>
            {busy ? "Saving…" : "Save social"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

export default function SettingsPage() {
  const { workspace, workspaces, refresh } = useWorkspace();
  const [members, setMembers] = useState<Member[]>([]);
  const [invites, setInvites] = useState<Invite[]>([]);
  const [error, setError] = useState("");
  const [inviteLink, setInviteLink] = useState("");
  const canAdmin = workspace && ["owner", "admin"].includes(workspace.role);

  async function load() {
    if (!workspace) return;
    const [nextMembers, nextInvites] = await Promise.all([
      api.members(workspace.id),
      canAdmin ? api.invites(workspace.id) : Promise.resolve([]),
    ]);
    setMembers(nextMembers);
    setInvites(nextInvites);
  }

  useEffect(() => {
    load().catch((err) => setError(err instanceof Error ? err.message : "Failed to load"));
  }, [workspace?.id]);

  async function invite(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!workspace) return;
    const form = new FormData(event.currentTarget);
    try {
      const created = await api.createInvite(
        workspace.id,
        String(form.get("email")),
        String(form.get("role")),
      );
      setInviteLink(`${window.location.origin}/invites/${created.token}`);
      event.currentTarget.reset();
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Invite failed");
    }
  }

  return (
    <AppShell>
      <h1 className="mb-6 text-2xl font-semibold tracking-tight">Settings</h1>
      <div className="grid gap-6">
        <Card>
          <CardHeader>
            <CardTitle>Workspace</CardTitle>
            <CardDescription>Team roles are enforced on the API, not only in this UI.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm">
              {workspace?.name} · your role <Badge>{workspace?.role}</Badge>
            </p>
            <form
              className="flex max-w-md gap-2"
              onSubmit={async (event) => {
                event.preventDefault();
                const name = String(new FormData(event.currentTarget).get("name") || "");
                if (!name) return;
                await api.createWorkspace(name);
                await refresh();
              }}
            >
              <Input name="name" placeholder="New workspace name" />
              <Button type="submit" variant="outline">
                Create
              </Button>
            </form>
            <p className="text-xs text-muted-foreground">{workspaces.length} workspace(s)</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Members</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {members.map((member) => (
              <div key={member.id} className="flex items-center justify-between gap-3 rounded-lg border px-3 py-2">
                <div>
                  <p className="text-sm font-medium">{member.name}</p>
                  <p className="text-xs text-muted-foreground">{member.email}</p>
                </div>
                <div className="flex items-center gap-2">
                  {canAdmin ? (
                    <select
                      className="h-9 rounded-md border bg-background px-2 text-sm"
                      value={member.role}
                      onChange={async (event) => {
                        if (!workspace) return;
                        await api.updateMember(workspace.id, member.user_id, event.target.value);
                        await load();
                      }}
                    >
                      <option value="owner">owner</option>
                      <option value="admin">admin</option>
                      <option value="editor">editor</option>
                      <option value="viewer">viewer</option>
                    </select>
                  ) : (
                    <Badge>{member.role}</Badge>
                  )}
                  {canAdmin ? (
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={async () => {
                        if (!workspace) return;
                        await api.removeMember(workspace.id, member.user_id);
                        await load();
                      }}
                    >
                      Remove
                    </Button>
                  ) : null}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>

        {canAdmin ? (
          <Card>
            <CardHeader>
              <CardTitle>Invite teammate</CardTitle>
              <CardDescription>They register with the invited email, then open the invite link.</CardDescription>
            </CardHeader>
            <CardContent>
              <form className="grid max-w-xl gap-3 sm:grid-cols-[1fr_140px_auto]" onSubmit={invite}>
                <Input name="email" type="email" required placeholder="teammate@company.com" />
                <select name="role" className="h-10 rounded-md border bg-background px-2 text-sm" defaultValue="editor">
                  <option value="admin">admin</option>
                  <option value="editor">editor</option>
                  <option value="viewer">viewer</option>
                </select>
                <Button type="submit">Send invite</Button>
              </form>
              {inviteLink ? (
                <p className="mt-3 break-all text-sm text-muted-foreground">Invite link: {inviteLink}</p>
              ) : null}
              <div className="mt-4 space-y-2">
                {invites.map((inviteItem) => (
                  <div key={inviteItem.id} className="flex items-center justify-between text-sm">
                    <span>
                      {inviteItem.email} · {inviteItem.role} · {inviteItem.status}
                    </span>
                    {inviteItem.status === "pending" ? (
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={async () => {
                          if (!workspace) return;
                          await api.revokeInvite(workspace.id, inviteItem.id);
                          await load();
                        }}
                      >
                        Revoke
                      </Button>
                    ) : null}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        ) : null}

        {error ? <p className="text-sm text-destructive">{error}</p> : null}

        <ProviderKeysCard />
        <StripeCard />
        <SocialCard />

        <Card>
          <CardHeader>
            <CardTitle>Billing</CardTitle>
            <CardDescription>Credits, plans, and the workspace ledger.</CardDescription>
          </CardHeader>
          <CardContent>
            <a href="/billing" className="text-sm underline">
              Open billing
            </a>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Legacy UI</CardTitle>
            <CardDescription>Streamlit remains available on port 8501.</CardDescription>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            Billing and credits stay in Phase 3. Team access is live now.
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}
