"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/app-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import { useWorkspace } from "@/lib/workspace";

type Scene = {
  id: string;
  order: number;
  duration: number;
  narration: string;
  visual_type: string;
  visual_prompt: string;
  visual_query: string;
  caption?: string;
};

type VideoPlan = {
  title: string;
  duration: number;
  aspect_ratio: string;
  visual_mode: string;
  scenes: Scene[];
};

type Capabilities = {
  ai_video: boolean;
  ai_image: boolean;
  message: string;
  providers: Array<{ name: string; kind: string; models: string[]; aspect_ratios: string[]; durations: number[] }>;
};

export default function DirectorPage() {
  const router = useRouter();
  const { workspace } = useWorkspace();
  const [topic, setTopic] = useState("");
  const [duration, setDuration] = useState(30);
  const [aspect, setAspect] = useState("9:16");
  const [style, setStyle] = useState("cinematic");
  const [tone, setTone] = useState("informative");
  const [platform, setPlatform] = useState("short");
  const [visualMode, setVisualMode] = useState("auto");
  const [plan, setPlan] = useState<VideoPlan | null>(null);
  const [script, setScript] = useState("");
  const [summary, setSummary] = useState("");
  const [caps, setCaps] = useState<Capabilities | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.aiCapabilities().then(setCaps).catch(() => setCaps(null));
  }, []);

  async function draft() {
    if (!workspace || !topic.trim()) return;
    setBusy(true);
    setError("");
    try {
      const result = await api.directorPlan({
        workspace_id: workspace.id,
        topic: topic.trim(),
        video_language: "en-US",
        duration,
        aspect_ratio: aspect,
        style,
        tone,
        target_platform: platform,
        visual_mode: visualMode,
      });
      setPlan(result.video_plan);
      setScript(result.script);
      setSummary(result.plan);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Director draft failed");
    } finally {
      setBusy(false);
    }
  }

  function updateScene(index: number, patch: Partial<Scene>) {
    setPlan((current) => {
      if (!current) return current;
      const scenes = current.scenes.map((scene, sceneIndex) =>
        sceneIndex === index ? { ...scene, ...patch } : scene,
      );
      return { ...current, scenes };
    });
  }

  async function generate() {
    if (!workspace || !plan) return;
    setBusy(true);
    setError("");
    try {
      const projects = await api.projects(workspace.id);
      const project =
        projects[0] ||
        (await api.createProject({ workspace_id: workspace.id, name: "Director", description: "AI Director" }));
      const video = await api.createVideo({
        workspace_id: workspace.id,
        project_id: project.id,
        title: plan.title || topic.trim(),
        topic: topic.trim(),
        duration: plan.duration,
        aspect_ratio: plan.aspect_ratio,
        visual_mode: visualMode,
        video_script: script,
        director_plan: plan,
      });
      router.push(`/videos/${video.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start generation");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AppShell>
      <div className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight">AI Director</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Plan scenes, then render with the existing ShortGen engine. AI clips are optional scene inputs.
        </p>
      </div>
      {caps && !caps.ai_video ? (
        <p className="mb-4 text-sm text-destructive">{caps.message || "AI video generation is temporarily unavailable."}</p>
      ) : null}
      <Card className="max-w-3xl">
        <CardHeader>
          <CardTitle>Brief</CardTitle>
          <CardDescription>AUTO mixes stock, stills, and AI video. STOCK ONLY keeps the original pipeline.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Input value={topic} onChange={(event) => setTopic(event.target.value)} placeholder="Create a cinematic 30-second video about…" />
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="space-y-1">
              <Label>Duration</Label>
              <Input type="number" min={8} max={120} value={duration} onChange={(event) => setDuration(Number(event.target.value))} />
            </div>
            <div className="space-y-1">
              <Label>Aspect</Label>
              <select className="flex h-10 w-full rounded-md border bg-background px-3 text-sm" value={aspect} onChange={(event) => setAspect(event.target.value)}>
                <option value="9:16">9:16</option>
                <option value="16:9">16:9</option>
                <option value="1:1">1:1</option>
              </select>
            </div>
            <div className="space-y-1">
              <Label>Visual mode</Label>
              <select className="flex h-10 w-full rounded-md border bg-background px-3 text-sm" value={visualMode} onChange={(event) => setVisualMode(event.target.value)}>
                <option value="auto">AUTO</option>
                <option value="stock">STOCK ONLY</option>
                <option value="mixed">MIXED</option>
                <option value="ai_video">AI VIDEO</option>
              </select>
            </div>
          </div>
          <div className="grid gap-3 sm:grid-cols-3">
            <Input value={style} onChange={(event) => setStyle(event.target.value)} placeholder="Style" />
            <Input value={tone} onChange={(event) => setTone(event.target.value)} placeholder="Tone" />
            <Input value={platform} onChange={(event) => setPlatform(event.target.value)} placeholder="Platform" />
          </div>
          <Button type="button" onClick={draft} disabled={busy || !topic.trim()}>
            {busy ? "Planning…" : "Draft plan"}
          </Button>
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
        </CardContent>
      </Card>

      {plan ? (
        <div className="mt-8 max-w-3xl space-y-4">
          {plan.scenes.map((scene, index) => (
            <Card key={scene.id || index}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base">Scene {scene.order}</CardTitle>
                  <Badge>{scene.visual_type}</Badge>
                </div>
                <CardDescription>{scene.duration}s</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <Textarea value={scene.narration} onChange={(event) => updateScene(index, { narration: event.target.value })} />
                <select
                  className="flex h-10 w-full rounded-md border bg-background px-3 text-sm"
                  value={scene.visual_type}
                  onChange={(event) => updateScene(index, { visual_type: event.target.value })}
                >
                  <option value="stock">stock</option>
                  <option value="ai_image">ai_image</option>
                  <option value="ai_video">ai_video</option>
                  <option value="user_asset">user_asset</option>
                </select>
                <Textarea value={scene.visual_prompt} onChange={(event) => updateScene(index, { visual_prompt: event.target.value })} />
              </CardContent>
            </Card>
          ))}
          <Button type="button" onClick={generate} disabled={busy}>
            {busy ? "Starting…" : "Generate video"}
          </Button>
          {summary ? <p className="whitespace-pre-wrap text-xs text-muted-foreground">{summary}</p> : null}
        </div>
      ) : null}
    </AppShell>
  );
}
