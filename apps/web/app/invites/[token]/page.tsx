"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api, getToken } from "@/lib/api";

export default function InvitePage() {
  const params = useParams<{ token: string }>();
  const router = useRouter();
  const [preview, setPreview] = useState<{ workspace_name: string; email: string; role: string; status: string } | null>(
    null,
  );
  const [error, setError] = useState("");

  useEffect(() => {
    api.previewInvite(params.token).then(setPreview).catch((err) => {
      setError(err instanceof Error ? err.message : "Invite not found");
    });
  }, [params.token]);

  async function accept() {
    if (!getToken()) {
      router.push(`/login?next=/invites/${params.token}`);
      return;
    }
    try {
      await api.acceptInvite(params.token);
      router.replace("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not accept invite");
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Workspace invite</CardTitle>
          <CardDescription>
            {preview
              ? `Join ${preview.workspace_name} as ${preview.role}. Invited email: ${preview.email}.`
              : "Checking invite…"}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
          <Button className="w-full" onClick={accept} disabled={!preview || preview.status !== "pending"}>
            Accept invite
          </Button>
          <p className="text-sm text-muted-foreground">
            Need an account first? <Link href="/register">Register</Link> with the invited email.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
