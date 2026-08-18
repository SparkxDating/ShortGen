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
  const [publishNote, setPublishNote] = useState("");
  const [platforms, setPlatforms] = useState<string[]>(["tiktok", "instagram", "youtube"]);
  const [scenes, setScenes] = useState<Array<{ id: string; order: number; visual_type: string; narration: string; status: string }>>([]);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const next = await api.video(params.id);
        if (!cancelled) setVideo(next);
        try {
          const nextScenes = await api.videoScenes(params.id);
          if (!cancelled) setScenes(nextScenes as Array<{ id: string; order: number; visual_type: string; narration: string; status: string }>);
        } catch {
          if (!cancelled) setScenes([]);
        }
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

  async function publish() {
    setBusy(true);
    setPublishNote("");
    try {
      const result = await api.publishVideo(params.id, platforms);
      if (result.success) {
        setPublishNote(`Posted to ${(result.platforms || []).join(", ") || "TikTok, Instagram, YouTube"}.`);
      } else if (!result.configured) {
        setPublishNote(
          "Open Settings → Post to TikTok, Instagram, YouTube. Create an Upload-Post account, connect those apps, then paste the API key and username.",
        );
      } else {
        setError(result.error || "Publish failed");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not publish");
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
                <div className="space-y-3">
                  <div className="flex flex-wrap gap-4 text-sm">
                    {["tiktok", "instagram", "youtube"].map((name) => (
                      <label key={name} className="flex items-center gap-2 capitalize">
                        <input
                          type="checkbox"
                          checked={platforms.includes(name)}
                          onChange={() =>
                            setPlatforms((current) =>
                              current.includes(name) ? current.filter((item) => item !== name) : [...current, name],
                            )
                          }
                        />
                        {name}
                      </label>
                    ))}
                  </div>
                  <div className="flex gap-2">
                    <a href={media} download>
                      <Button variant="secondary">Download</Button>
                    </a>
                    <Button variant="outline" disabled={busy || platforms.length === 0} onClick={publish}>
                      Publish
                    </Button>
                  </div>
                </div>
                {publishNote ? <p className="text-sm text-muted-foreground">{publishNote}</p> : null}
                {scenes.length ? (
                  <div className="space-y-2">
                    <p className="text-sm font-medium">Scenes</p>
                    {scenes.map((scene) => (
                      <div key={scene.id} className="flex items-center justify-between gap-2 rounded-md border px-3 py-2 text-sm">
                        <span>
                          {scene.order}. [{scene.visual_type}] {scene.narration}
                        </span>
                        <Button
                          size="sm"
                          variant="outline"
                          disabled={busy}
                          onClick={async () => {
                            setBusy(true);
                            try {
                              await api.regenerateScene(params.id, scene.id);
                              setPublishNote("Scene regenerating. Other scenes are kept.");
                            } catch (err) {
                              setError(err instanceof Error ? err.message : "Regenerate failed");
                            } finally {
                              setBusy(false);
                            }
                          }}
                        >
                          Regenerate
                        </Button>
                      </div>
                    ))}
                  </div>
                ) : null}
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
