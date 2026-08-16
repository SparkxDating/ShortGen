"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { EmptyState } from "@/components/empty-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import type { Project, Video } from "@/lib/types";

export default function ProjectDetailPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const [project, setProject] = useState<Project | null>(null);
  const [videos, setVideos] = useState<Video[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api.project(params.id), api.videos({ project_id: params.id })])
      .then(([nextProject, nextVideos]) => {
        setProject(nextProject);
        setVideos(nextVideos);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Not found"));
  }, [params.id]);

  async function remove() {
    if (!confirm("Delete this project and its videos?")) return;
    await api.deleteProject(params.id);
    router.replace("/projects");
  }

  return (
    <AppShell>
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      {project ? (
        <>
          <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
            <div>
              <h1 className="text-2xl font-semibold tracking-tight">{project.name}</h1>
              <p className="mt-1 text-sm text-muted-foreground">
                {project.description || "No description"}
              </p>
            </div>
            <div className="flex gap-2">
              <Link href="/create">
                <Button>Create video</Button>
              </Link>
              <Button variant="outline" onClick={remove}>
                Delete
              </Button>
            </div>
          </div>
          <Card>
            <CardHeader>
              <CardTitle>Videos</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              {videos.length === 0 ? (
                <EmptyState
                  title="No videos in this project"
                  description="Generate a video and it will appear here."
                />
              ) : (
                videos.map((video) => (
                  <Link
                    key={video.id}
                    href={`/videos/${video.id}`}
                    className="flex items-center justify-between rounded-lg border border-border px-3 py-3 text-sm hover:bg-accent"
                  >
                    <span>{video.title}</span>
                    <Badge>{video.status}</Badge>
                  </Link>
                ))
              )}
            </CardContent>
          </Card>
        </>
      ) : null}
    </AppShell>
  );
}
