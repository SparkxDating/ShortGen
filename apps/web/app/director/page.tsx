"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/app-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { api } from "@/lib/api";
import { useWorkspace } from "@/lib/workspace";

type Provider = { id: string; label: string; status: string; notes?: string };

export default function DirectorPage() {
  const router = useRouter();
  const { workspace } = useWorkspace();
  const [topic, setTopic] = useState("");
  const [plan, setPlan] = useState("");
  const [script, setScript] = useState("");
  const [providers, setProviders] = useState<Provider[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.directorProviders().then(setProviders).catch(() => setProviders([]));
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
      });
      setPlan(result.plan);
      setScript(result.script);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Director draft failed");
    } finally {
      setBusy(false);
    }
  }

  function generate() {
    if (!topic.trim()) return;
    const query = new URLSearchParams({ topic: topic.trim() });
    router.push(`/create?${query.toString()}`);
  }

  return (
    <AppShell>
      <div className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight">AI Director</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Plan a short. Rendering still goes through the existing ShortGen engine.
        </p>
      </div>
      <Card className="max-w-2xl">
        <CardHeader>
          <CardTitle>Brief</CardTitle>
          <CardDescription>A first-pass shot list, not a second renderer.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Input value={topic} onChange={(event) => setTopic(event.target.value)} placeholder="Topic" />
          <div className="flex gap-2">
            <Button type="button" onClick={draft} disabled={busy || !topic.trim()}>
              {busy ? "Planning…" : "Draft plan"}
            </Button>
            {script ? (
              <Button type="button" variant="outline" onClick={generate}>
                Generate with ShortGen
              </Button>
            ) : null}
          </div>
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
          {plan ? <Textarea value={plan} readOnly className="min-h-[240px]" /> : null}
        </CardContent>
      </Card>
      <div className="mt-8 grid max-w-2xl gap-3 md:grid-cols-2">
        {providers.map((provider) => (
          <Card key={provider.id}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-base">{provider.label}</CardTitle>
                <Badge tone={provider.status === "active" ? "success" : "muted"}>
                  {provider.status}
                </Badge>
              </div>
              <CardDescription>{provider.notes || "Not wired yet."}</CardDescription>
            </CardHeader>
          </Card>
        ))}
      </div>
    </AppShell>
  );
}
