"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { api, resolveMediaUrl } from "@/lib/api";
import type { Video } from "@/lib/types";
import { stageLabel } from "@/lib/utils";

export default function VideoDetailPage() {
  const params = useParams<{ id: string }>();
  const [video, setVideo] = useState<Video | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const next = await api.video(params.id);
        if (!cancelled) setVideo(next);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : "Video not found");
      }
    }
    load();
    const timer = window.setInterval(load, 2500);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [params.id]);

  const job = video?.latest_job;
  const running = job && ["QUEUED", "RUNNING"].includes(job.status);
  const media = resolveMediaUrl(video?.video_url);

  async function cancel() {
    if (!job) return;
    setBusy(true);
    try {
      await api.cancelJob(job.id);
      setVideo(await api.video(params.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not cancel");
    } finally {
      setBusy(false);
    }
  }

  async function retry() {
    if (!job) return;
    setBusy(true);
    try {
      await api.retryJob(job.id);
      setVideo(await api.video(params.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not retry");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppShell>
      {error ? <p className="mb-4 text-sm text-destructive">{error}</p> : null}
      {video ? (
        <Card className="max-w-3xl">
          <CardHeader>
            <div className="flex items-center justify-between gap-3">
              <div>
                <CardTitle>{job?.status === "COMPLETED" ? "Video ready" : "Generating your video"}</CardTitle>
                <CardDescription>{video.title}</CardDescription>
              </div>
              <Badge>{video.status}</Badge>
            </div>
          </CardHeader>
          <CardContent className="space-y-6">
            <div>
              <div className="mb-2 flex items-center justify-between text-sm">
                <span>{stageLabel(job?.current_stage)}</span>
                <span className="tabular-nums text-muted-foreground">{video.progress}%</span>
              </div>
              <Progress value={video.progress} />
              <p className="mt-2 text-sm text-muted-foreground">
                Current step: {stageLabel(job?.current_stage)}
              </p>
            </div>

            {job?.status === "FAILED" ? (
              <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-4 text-sm">
                <p className="font-medium">Generation failed</p>
                <p className="mt-1 text-muted-foreground">{job.error_message || "Unknown error"}</p>
                <Button className="mt-4" variant="outline" disabled={busy} onClick={retry}>
                  Retry job
                </Button>
              </div>
            ) : null}

            {running ? (
              <Button variant="outline" disabled={busy} onClick={cancel}>
                Cancel
              </Button>
            ) : null}

            {job?.status === "COMPLETED" && media ? (
              <div className="space-y-4">
                <video className="w-full rounded-lg border border-border" src={media} controls />
                <a href={media} download>
                  <Button variant="secondary">Download</Button>
                </a>
              </div>
            ) : null}
          </CardContent>
        </Card>
      ) : (
        <p className="text-sm text-muted-foreground">Loading generation status…</p>
      )}
    </AppShell>
  );
}
