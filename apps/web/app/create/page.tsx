"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, Suspense, useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import type { Asset, Project, Template } from "@/lib/types";
import { useWorkspace } from "@/lib/workspace";

const VOICES = [
  "en-US-JennyNeural-Female",
  "en-US-GuyNeural-Male",
  "zh-CN-XiaoxiaoNeural-Female",
  "zh-CN-YunxiNeural-Male",
];

function CreateForm() {
  const router = useRouter();
  const search = useSearchParams();
  const { workspace, workspaces, setWorkspaceId } = useWorkspace();
  const [projects, setProjects] = useState<Project[]>([]);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [selectedAssets, setSelectedAssets] = useState<string[]>([]);
  const [visualSource, setVisualSource] = useState("stock");
  const [script, setScript] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [estimate, setEstimate] = useState<number | null>(null);
  const workspaceId = workspace?.id || "";

  useEffect(() => {
    if (!workspaceId) return;
    Promise.all([api.projects(workspaceId), api.templates(workspaceId), api.assets(workspaceId)])
      .then(([nextProjects, nextTemplates, nextAssets]) => {
        setProjects(nextProjects);
        setTemplates(nextTemplates);
        setAssets(nextAssets);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load"));
  }, [workspaceId]);

  useEffect(() => {
    const templateId = search.get("template");
    if (!templateId || templates.length === 0) return;
    const template = templates.find((item) => item.id === templateId);
    if (!template) return;
    const form = document.getElementById("create-form") as HTMLFormElement | null;
    if (!form) return;
    const config = template.config;
    if (config.aspect_ratio) form.aspect_ratio.value = String(config.aspect_ratio);
    if (config.duration) form.duration.value = String(config.duration);
    if (config.resolution) form.resolution.value = String(config.resolution);
    if (config.voice) form.voice.value = String(config.voice);
    if (config.visual_source) {
      form.visual_source.value = String(config.visual_source);
      setVisualSource(String(config.visual_source));
    }
    form.template_id.value = template.id;
  }, [search, templates]);

  async function preview() {
    if (!workspaceId) return;
    const form = document.getElementById("create-form") as HTMLFormElement;
    const topic = String(new FormData(form).get("topic") || "");
    if (!topic) {
      setError("Add a topic before previewing the script");
      return;
    }
    setPreviewing(true);
    setError("");
    try {
      const result = await api.previewScript({
        workspace_id: workspaceId,
        topic,
        video_language: String(new FormData(form).get("video_language") || "en-US"),
      });
      setScript(result.script);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Script preview failed");
    } finally {
      setPreviewing(false);
    }
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setLoading(true);
    const form = new FormData(event.currentTarget);
    try {
      const video = await api.createVideo({
        workspace_id: String(form.get("workspace_id")),
        project_id: String(form.get("project_id")),
        title: String(form.get("title")),
        topic: String(form.get("topic")),
        video_language: String(form.get("video_language")),
        duration: Number(form.get("duration")),
        aspect_ratio: String(form.get("aspect_ratio")),
        resolution: String(form.get("resolution")),
        voice: String(form.get("voice")),
        visual_source: String(form.get("visual_source")),
        video_script: script,
        template_id: String(form.get("template_id") || "") || null,
        asset_ids: visualSource === "local" ? selectedAssets : [],
      });
      router.push(`/videos/${video.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start generation");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AppShell>
      <div className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight">Create video</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Optional script preview uses the existing LLM path. Render still happens in the worker.
        </p>
      </div>
      <Card className="max-w-2xl">
        <CardHeader>
          <CardTitle>Brief</CardTitle>
          <CardDescription>Topic, voice, aspect ratio, and media source for your short.</CardDescription>
        </CardHeader>
        <CardContent>
          <form id="create-form" className="grid gap-5" onSubmit={onSubmit}>
            <input type="hidden" name="template_id" defaultValue={search.get("template") || ""} />
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="workspace_id">Workspace</Label>
                <select
                  id="workspace_id"
                  name="workspace_id"
                  value={workspaceId}
                  onChange={(event) => setWorkspaceId(event.target.value)}
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                >
                  {workspaces.map((item) => (
                    <option key={item.id} value={item.id}>
                      {item.name}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="project_id">Project</Label>
                <select
                  id="project_id"
                  name="project_id"
                  required
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                >
                  {projects.map((project) => (
                    <option key={project.id} value={project.id}>
                      {project.name}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="template_select">Template</Label>
              <select
                id="template_select"
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                defaultValue={search.get("template") || ""}
                onChange={(event) => {
                  const form = event.currentTarget.form;
                  if (form) form.template_id.value = event.target.value;
                  const template = templates.find((item) => item.id === event.target.value);
                  if (!template || !form) return;
                  if (template.config.aspect_ratio) form.aspect_ratio.value = String(template.config.aspect_ratio);
                  if (template.config.duration) form.duration.value = String(template.config.duration);
                  if (template.config.voice) form.voice.value = String(template.config.voice);
                  if (template.config.visual_source) {
                    form.visual_source.value = String(template.config.visual_source);
                    setVisualSource(String(template.config.visual_source));
                  }
                }}
              >
                <option value="">None</option>
                {templates.map((template) => (
                  <option key={template.id} value={template.id}>
                    {template.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="topic">Topic</Label>
              <Input id="topic" name="topic" required placeholder="Why the ocean is blue" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="title">Title</Label>
              <Input id="title" name="title" required placeholder="Ocean facts" />
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="video_language">Video language</Label>
                <Input id="video_language" name="video_language" defaultValue="en-US" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="duration">Duration (seconds)</Label>
                <Input id="duration" name="duration" type="number" min={5} max={300} defaultValue={30} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="aspect_ratio">Aspect ratio</Label>
                <select
                  id="aspect_ratio"
                  name="aspect_ratio"
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                  defaultValue="9:16"
                >
                  <option value="9:16">9:16</option>
                  <option value="16:9">16:9</option>
                  <option value="1:1">1:1</option>
                </select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="resolution">Resolution</Label>
                <select
                  id="resolution"
                  name="resolution"
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                  defaultValue="1080p"
                >
                  <option value="1080p">1080p</option>
                  <option value="720p">720p</option>
                </select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="voice">Voice</Label>
                <select
                  id="voice"
                  name="voice"
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                >
                  {VOICES.map((voice) => (
                    <option key={voice} value={voice}>
                      {voice}
                    </option>
                  ))}
                </select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="visual_source">Visual source</Label>
                <select
                  id="visual_source"
                  name="visual_source"
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                  value={visualSource}
                  onChange={(event) => setVisualSource(event.target.value)}
                >
                  <option value="stock">Stock Media</option>
                  <option value="local">Local Media</option>
                </select>
              </div>
            </div>
            {visualSource === "local" ? (
              <div className="space-y-2">
                <Label>Workspace assets</Label>
                {assets.length === 0 ? (
                  <p className="text-sm text-muted-foreground">Upload files in Library first.</p>
                ) : (
                  <div className="grid gap-2">
                    {assets.map((asset) => (
                      <label key={asset.id} className="flex items-center gap-2 text-sm">
                        <input
                          type="checkbox"
                          checked={selectedAssets.includes(asset.id)}
                          onChange={(event) => {
                            setSelectedAssets((current) =>
                              event.target.checked
                                ? [...current, asset.id]
                                : current.filter((id) => id !== asset.id),
                            );
                          }}
                        />
                        {asset.original_filename}
                      </label>
                    ))}
                  </div>
                )}
              </div>
            ) : null}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="script">Script (optional)</Label>
                <Button type="button" variant="outline" size="sm" onClick={preview} disabled={previewing}>
                  {previewing ? "Generating…" : "Preview script"}
                </Button>
              </div>
              <Textarea
                id="script"
                value={script}
                onChange={(event) => setScript(event.target.value)}
                placeholder="Leave empty to generate during the job, or preview first."
              />
            </div>
            {error ? <p className="text-sm text-destructive">{error}</p> : null}
            <p className="text-sm text-muted-foreground">
              Estimated cost: {estimate ?? "—"} credits. Held on start, refunded if generation fails.
            </p>
            <Button
              type="button"
              variant="outline"
              onClick={async () => {
                const form = document.getElementById("create-form") as HTMLFormElement;
                const data = new FormData(form);
                const result = await api.estimate(Number(data.get("duration") || 30), String(data.get("resolution")));
                setEstimate(result.credits);
              }}
            >
              Recalculate credits
            </Button>
            <Button type="submit" disabled={loading || projects.length === 0}>
              {loading ? "Starting…" : "Generate Video"}
            </Button>
            {projects.length === 0 ? (
              <p className="text-sm text-muted-foreground">Create a project first.</p>
            ) : null}
          </form>
        </CardContent>
      </Card>
    </AppShell>
  );
}

export default function CreatePage() {
  return (
    <Suspense fallback={<div className="p-8 text-sm text-muted-foreground">Loading…</div>}>
      <CreateForm />
    </Suspense>
  );
}
