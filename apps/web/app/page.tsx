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
          A topic in. A short out. Voice, captions, and a file ready to post.
        </h1>
        <p className="mt-5 max-w-2xl text-lg text-muted-foreground">
          Turn a topic into a short with voice and captions. A 30-second HD short costs 25 credits.
          New studios start with 100 credits, then subscribe for a fresh monthly allowance.
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
        <div className="mt-16 grid gap-4 md:grid-cols-3">
          {[
            { name: "Free", price: "$0", detail: "100 credits to start. About four HD shorts." },
            { name: "Starter", price: "$19/mo", detail: "500 credits every month. About twenty HD shorts." },
            { name: "Pro", price: "$49/mo", detail: "2,000 credits every month. About eighty HD shorts." },
          ].map((plan) => (
            <div key={plan.name} className="rounded-xl border p-5">
              <p className="text-sm font-medium">{plan.name}</p>
              <p className="mt-2 text-2xl font-semibold">{plan.price}</p>
              <p className="mt-2 text-sm text-muted-foreground">{plan.detail}</p>
            </div>
          ))}
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
              Starter and Pro renew monthly. Credits land when Stripe confirms the invoice.
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
