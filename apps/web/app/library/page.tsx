"use client";

import { FormEvent, useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { EmptyState } from "@/components/empty-state";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api, resolveMediaUrl } from "@/lib/api";
import type { Asset } from "@/lib/types";
import { useWorkspace } from "@/lib/workspace";

export default function LibraryPage() {
  const { workspace } = useWorkspace();
  const [assets, setAssets] = useState<Asset[]>([]);
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);

  async function refresh() {
    if (!workspace) return;
    setAssets(await api.assets(workspace.id));
  }

  useEffect(() => {
    refresh().catch((err) => setError(err instanceof Error ? err.message : "Failed to load"));
  }, [workspace?.id]);

  async function onUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!workspace) return;
    const form = new FormData(event.currentTarget);
    const file = form.get("file");
    if (!(file instanceof File) || !file.size) return;
    setUploading(true);
    setError("");
    try {
      await api.uploadAsset(workspace.id, file);
      event.currentTarget.reset();
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
    }
  }

  return (
    <AppShell>
      <div className="mb-8 flex items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Library</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Workspace media for local-generation jobs. Isolated per workspace.
          </p>
        </div>
      </div>
      <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
        <Card>
          <CardHeader>
            <CardTitle>Upload</CardTitle>
          </CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={onUpload}>
              <input
                name="file"
                type="file"
                required
                accept=".mp4,.mov,.webm,.mkv,.jpg,.jpeg,.png,.webp,.mp3,.wav,.m4a"
                className="block w-full text-sm"
              />
              <p className="text-xs text-muted-foreground">Max 100MB. Video, image, or audio.</p>
              <Button type="submit" disabled={uploading || !workspace} className="w-full">
                {uploading ? "Uploading…" : "Upload file"}
              </Button>
            </form>
          </CardContent>
        </Card>
        <div className="space-y-3">
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
          {assets.length === 0 ? (
            <EmptyState
              title="No assets yet"
              description="Upload local clips to use instead of stock footage."
            />
          ) : (
            assets.map((asset) => (
              <Card key={asset.id}>
                <CardContent className="flex items-center justify-between gap-4 p-4">
                  <div>
                    <p className="text-sm font-medium">{asset.original_filename}</p>
                    <p className="text-xs text-muted-foreground">
                      {(asset.size_bytes / 1024 / 1024).toFixed(2)} MB
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge>{asset.kind}</Badge>
                    <a className="text-sm underline" href={resolveMediaUrl(asset.public_url) || "#"}>
                      Open
                    </a>
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={async () => {
                        await api.deleteAsset(asset.id);
                        await refresh();
                      }}
                    >
                      Delete
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </div>
      </div>
    </AppShell>
  );
}
