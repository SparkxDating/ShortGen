"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { EmptyState } from "@/components/empty-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import type { Template } from "@/lib/types";
import { useWorkspace } from "@/lib/workspace";

export default function TemplatesPage() {
  const { workspace } = useWorkspace();
  const [templates, setTemplates] = useState<Template[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api
      .templates(workspace?.id)
      .then(setTemplates)
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load"));
  }, [workspace?.id]);

  return (
    <AppShell>
      <div className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight">Templates</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Presets for short-form formats. They wrap the existing generation engine.
        </p>
      </div>
      {error ? <p className="mb-4 text-sm text-destructive">{error}</p> : null}
      {templates.length === 0 ? (
        <EmptyState title="No templates" description="System templates seed on API startup." />
      ) : (
        <div className="grid gap-4 md:grid-cols-2">
          {templates.map((template) => (
            <Card key={template.id}>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle>{template.name}</CardTitle>
                  <Badge>{template.is_system ? "system" : "workspace"}</Badge>
                </div>
                <CardDescription>{template.description}</CardDescription>
              </CardHeader>
              <CardContent className="flex items-center justify-between">
                <p className="text-xs text-muted-foreground">
                  {String(template.config.aspect_ratio || "9:16")} · {String(template.config.duration || 30)}s
                </p>
                <Link href={`/create?template=${template.id}`}>
                  <Button size="sm">Use template</Button>
                </Link>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </AppShell>
  );
}
