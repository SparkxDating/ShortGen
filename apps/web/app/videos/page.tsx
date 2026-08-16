"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { EmptyState } from "@/components/empty-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { api } from "@/lib/api";
import type { Video } from "@/lib/types";
import { useWorkspace } from "@/lib/workspace";
import { formatDate } from "@/lib/utils";

export default function VideosPage() {
  const { workspace } = useWorkspace();
  const [videos, setVideos] = useState<Video[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!workspace) return;
    api
      .videos({ workspace_id: workspace.id })
      .then(setVideos)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load"));
  }, [workspace?.id]);

  return (
    <AppShell>
      <div className="mb-8 flex items-end justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Videos</h1>
          <p className="mt-1 text-sm text-muted-foreground">Every generation in this workspace.</p>
        </div>
        <Link href="/create">
          <Button>Create video</Button>
        </Link>
      </div>
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      {videos.length === 0 ? (
        <EmptyState title="No videos" description="Generate a video to populate this library." />
      ) : (
        <div className="space-y-3">
          {videos.map((video) => (
            <Link key={video.id} href={`/videos/${video.id}`}>
              <Card className="transition-colors hover:bg-accent/40">
                <CardContent className="flex items-center justify-between p-4">
                  <div>
                    <p className="font-medium">{video.title}</p>
                    <p className="text-xs text-muted-foreground">
                      {video.aspect_ratio} · {formatDate(video.created_at)}
                    </p>
                  </div>
                  <Badge>{video.status}</Badge>
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </AppShell>
  );
}
