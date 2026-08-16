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
