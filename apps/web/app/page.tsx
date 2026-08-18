"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { getToken } from "@/lib/api";

export default function HomePage() {
  const [signedIn, setSignedIn] = useState(false);

  useEffect(() => {
    setSignedIn(Boolean(getToken()));
  }, []);

  return (
    <div className="min-h-screen bg-background">
      <header className="mx-auto flex max-w-5xl items-center justify-between px-6 py-6">
        <p className="text-sm font-semibold tracking-[0.2em] uppercase">ShortGen</p>
        <div className="flex gap-2">
          {signedIn ? (
            <Link href="/dashboard">
              <Button>Open studio</Button>
            </Link>
          ) : (
            <>
              <Link href="/login">
                <Button variant="outline">Sign in</Button>
              </Link>
              <Link href="/register">
                <Button>Create account</Button>
              </Link>
            </>
          )}
        </div>
      </header>
      <main className="mx-auto max-w-5xl px-6 py-16">
        <p className="text-xs uppercase tracking-[0.25em] text-muted-foreground">AI short-form studio</p>
        <h1 className="mt-4 max-w-3xl text-4xl font-semibold tracking-tight sm:text-5xl">
          Generate videos. Charge with Stripe. Post to TikTok, Instagram, and YouTube.
        </h1>
        <p className="mt-5 max-w-2xl text-lg text-muted-foreground">
          Create an account, spend workspace credits, and render with the same MoneyPrinterTurbo engine.
          New studios start with 100 credits.
        </p>
        <div className="mt-8 flex flex-wrap gap-3">
          <Link href="/register">
            <Button size="lg">Start generating</Button>
          </Link>
          <Link href="/login">
            <Button size="lg" variant="outline">
              I already have an account
            </Button>
          </Link>
        </div>
        <div className="mt-16 grid gap-6 md:grid-cols-3">
          <div className="rounded-xl border p-5">
            <p className="text-sm font-medium">Generate</p>
            <p className="mt-2 text-sm text-muted-foreground">
              Topic to script, Pexels clips, voice, and captions. Your workspace is isolated.
            </p>
          </div>
          <div className="rounded-xl border p-5">
            <p className="text-sm font-medium">Stripe billing</p>
            <p className="mt-2 text-sm text-muted-foreground">
              Buy credit packs or a plan. Credits land only after Stripe confirms the webhook.
            </p>
          </div>
          <div className="rounded-xl border p-5">
            <p className="text-sm font-medium">Post</p>
            <p className="mt-2 text-sm text-muted-foreground">
              Publish a finished video to TikTok, Instagram, and YouTube from the video page.
            </p>
          </div>
        </div>
      </main>
    </div>
  );
}
