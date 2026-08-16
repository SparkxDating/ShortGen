"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { EmptyState } from "@/components/empty-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { api } from "@/lib/api";
import type { Project, Usage, Video } from "@/lib/types";
import { useWorkspace } from "@/lib/workspace";
import { formatDate, stageLabel } from "@/lib/utils";

function statusTone(status: string) {
  if (status === "completed" || status === "COMPLETED") return "success" as const;
  if (status === "failed" || status === "FAILED") return "danger" as const;
  if (status === "cancelled" || status === "CANCELLED") return "muted" as const;
  if (status === "processing" || status === "RUNNING") return "warning" as const;
  return "default" as const;
}

export default function DashboardPage() {
  const { workspace } = useWorkspace();
  const [projects, setProjects] = useState<Project[]>([]);
  const [videos, setVideos] = useState<Video[]>([]);
  const [usage, setUsage] = useState<Usage | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const workspaceId = workspace?.id;
    Promise.all([
      api.projects(workspaceId),
      api.videos(workspaceId ? { workspace_id: workspaceId } : undefined),
      workspaceId ? api.usage(workspaceId) : Promise.resolve(null),
    ])
      .then(([nextProjects, nextVideos, nextUsage]) => {
        setProjects(nextProjects.slice(0, 5));
        setVideos(nextVideos.slice(0, 5));
        setUsage(nextUsage);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load dashboard"));
  }, [workspace?.id]);

  const active = videos.find((video) =>
    ["queued", "processing"].includes(video.status),
  );

  return (
    <AppShell>
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Dashboard</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Create, review, and monitor AI video generation.
          </p>
        </div>
        <Link href="/create">
          <Button>Create Video</Button>
        </Link>
      </div>

      {error ? <p className="mt-6 text-sm text-destructive">{error}</p> : null}

      <div className="mt-8 grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Generation status</CardTitle>
            <CardDescription>Live progress from the worker, not a fake timer.</CardDescription>
          </CardHeader>
          <CardContent>
            {active ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between text-sm">
                  <span>{active.title}</span>
                  <span className="text-muted-foreground">{active.progress}%</span>
                </div>
                <Progress value={active.progress} />
                <p className="text-sm text-muted-foreground">
                  {stageLabel(active.latest_job?.current_stage || active.status)}
                </p>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">No videos generating right now.</p>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Usage</CardTitle>
            <CardDescription>{usage?.plan?.name || "Free"} plan</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-end justify-between">
              <p className="text-3xl font-semibold">{usage?.available ?? "—"}</p>
              <span className="text-sm text-muted-foreground">credits</span>
            </div>
            <p className="text-sm text-muted-foreground">
              {usage?.credits_spent_this_period ?? 0} used this month · next video ~
              {usage?.estimated_next_video ?? 25} credits
            </p>
            <Link href="/billing">
              <Button variant="outline" size="sm">
                Manage billing
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>

      <div className="mt-8 grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Recent projects</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {projects.length === 0 ? (
              <EmptyState
                title="No projects yet"
                description="Create a project to group related videos."
                action={
                  <Link href="/projects">
                    <Button variant="outline" size="sm">
                      Open projects
                    </Button>
                  </Link>
                }
              />
            ) : (
              projects.map((project) => (
                <Link
                  key={project.id}
                  href={`/projects/${project.id}`}
                  className="flex items-center justify-between rounded-lg border border-border px-3 py-3 text-sm transition-colors hover:bg-accent"
                >
                  <span>{project.name}</span>
                  <span className="text-muted-foreground">{formatDate(project.updated_at)}</span>
                </Link>
              ))
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Recent videos</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {videos.length === 0 ? (
              <EmptyState
                title="No videos yet"
                description="Start from a topic. Generation runs in the background."
                action={
                  <Link href="/create">
                    <Button variant="outline" size="sm">
                      Create video
                    </Button>
                  </Link>
                }
              />
            ) : (
              videos.map((video) => (
                <Link
                  key={video.id}
                  href={`/videos/${video.id}`}
                  className="flex items-center justify-between rounded-lg border border-border px-3 py-3 text-sm transition-colors hover:bg-accent"
                >
                  <span>{video.title}</span>
                  <Badge tone={statusTone(video.status)}>{video.status}</Badge>
                </Link>
              ))
            )}
          </CardContent>
        </Card>
      </div>
    </AppShell>
  );
}
