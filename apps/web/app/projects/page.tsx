"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { EmptyState } from "@/components/empty-state";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import type { Project, Workspace } from "@/lib/types";
import { formatDate } from "@/lib/utils";

export default function ProjectsPage() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [error, setError] = useState("");

  async function refresh() {
    const [nextWorkspaces, nextProjects] = await Promise.all([api.workspaces(), api.projects()]);
    setWorkspaces(nextWorkspaces);
    setProjects(nextProjects);
  }

  useEffect(() => {
    refresh().catch((err) => setError(err instanceof Error ? err.message : "Failed to load"));
  }, []);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    try {
      await api.createProject({
        workspace_id: String(form.get("workspace_id") || workspaces[0]?.id || ""),
        name: String(form.get("name") || ""),
        description: String(form.get("description") || ""),
      });
      event.currentTarget.reset();
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create project");
    }
  }

  return (
    <AppShell>
      <div className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight">Projects</h1>
        <p className="mt-1 text-sm text-muted-foreground">Organize videos by campaign or channel.</p>
      </div>
      <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>New project</CardTitle>
          </CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={onSubmit}>
              <div className="space-y-2">
                <Label htmlFor="workspace_id">Workspace</Label>
                <select
                  id="workspace_id"
                  name="workspace_id"
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                  defaultValue={workspaces[0]?.id}
                >
                  {workspaces.map((workspace) => (
                    <option key={workspace.id} value={workspace.id}>
                      {workspace.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="name">Name</Label>
                <Input id="name" name="name" required />
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea id="description" name="description" />
              </div>
              <Button type="submit" className="w-full">
                Create project
              </Button>
            </form>
          </CardContent>
        </Card>
        <div className="space-y-3">
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
          {projects.length === 0 ? (
            <EmptyState
              title="Nothing here yet"
              description="Create your first project to start generating videos."
            />
          ) : (
            projects.map((project) => (
              <Link key={project.id} href={`/projects/${project.id}`}>
                <Card className="transition-colors hover:bg-accent/40">
                  <CardHeader>
                    <CardTitle>{project.name}</CardTitle>
                    <p className="text-sm text-muted-foreground">
                      {project.description || "No description"} · {formatDate(project.created_at)}
                    </p>
                  </CardHeader>
                </Card>
              </Link>
            ))
          )}
        </div>
      </div>
    </AppShell>
  );
}
