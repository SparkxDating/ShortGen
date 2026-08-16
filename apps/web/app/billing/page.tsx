"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/app-shell";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { api } from "@/lib/api";
import type { CreditPack, LedgerEntry, Plan, Usage } from "@/lib/types";
import { useWorkspace } from "@/lib/workspace";
import { formatDate } from "@/lib/utils";

function money(cents: number, currency: string) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: currency.toUpperCase(),
  }).format(cents / 100);
}

export default function BillingPage() {
  const { workspace } = useWorkspace();
  const [usage, setUsage] = useState<Usage | null>(null);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [packs, setPacks] = useState<CreditPack[]>([]);
  const [ledger, setLedger] = useState<LedgerEntry[]>([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");

  async function refresh() {
    if (!workspace) return;
    const [nextUsage, nextPlans, nextPacks, nextLedger] = await Promise.all([
      api.usage(workspace.id),
      api.plans(),
      api.packs(),
      api.ledger(workspace.id),
    ]);
    setUsage(nextUsage);
    setPlans(nextPlans);
    setPacks(nextPacks);
    setLedger(nextLedger);
  }

  useEffect(() => {
    refresh().catch((err) => setError(err instanceof Error ? err.message : "Failed to load billing"));
  }, [workspace?.id]);

  async function buy(kind: "pack" | "plan", itemId: string) {
    if (!workspace) return;
    setBusy(itemId);
    setError("");
    try {
      const result = await api.checkout(workspace.id, kind, itemId);
      if (result.provider !== "local" && result.checkout_url) {
        window.location.href = result.checkout_url;
        return;
      }
      if (result.provider !== "local" && !result.completed) {
        setError(result.message || "Complete payment with the billing provider. Credits are added only after a verified webhook.");
        return;
      }
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Checkout failed");
    } finally {
      setBusy("");
    }
  }

  const canBuy = workspace && ["owner", "admin"].includes(workspace.role);

  return (
    <AppShell>
      <div className="mb-8">
        <h1 className="text-2xl font-semibold tracking-tight">Billing</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Credits are workspace-scoped. Local mode completes purchases without Stripe or Razorpay.
        </p>
      </div>
      {error ? <p className="mb-4 text-sm text-destructive">{error}</p> : null}

      <div className="grid gap-6 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Available</CardTitle>
            <CardDescription>Ready to spend on generation.</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-semibold">{usage?.available ?? "—"}</p>
            <p className="mt-2 text-sm text-muted-foreground">{usage?.reserved ?? 0} reserved</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Plan</CardTitle>
            <CardDescription>{usage?.subscription_status || "none"}</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-xl font-medium">{usage?.plan?.name || "Free"}</p>
            <p className="mt-2 text-sm text-muted-foreground">
              {usage?.plan?.monthly_credits ?? 100} credits / month
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>This month</CardTitle>
            <CardDescription>Reserved generation credits.</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-semibold">{usage?.credits_spent_this_period ?? 0}</p>
            <p className="mt-2 text-sm text-muted-foreground">{usage?.videos_this_period ?? 0} videos started</p>
          </CardContent>
        </Card>
      </div>

      <h2 className="mb-4 mt-10 text-lg font-semibold">Plans</h2>
      <div className="grid gap-4 md:grid-cols-3">
        {plans.map((plan) => (
          <Card key={plan.id} className={usage?.plan?.id === plan.id ? "border-foreground" : ""}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>{plan.name}</CardTitle>
                {usage?.plan?.id === plan.id ? <Badge>current</Badge> : null}
              </div>
              <CardDescription>{plan.description}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-2xl font-semibold">
                {plan.price_cents === 0 ? "Free" : money(plan.price_cents, plan.currency)}
              </p>
              <p className="text-sm text-muted-foreground">{plan.monthly_credits} credits / month</p>
              {canBuy && plan.price_cents > 0 ? (
                <Button
                  className="w-full"
                  variant="outline"
                  disabled={busy === plan.id}
                  onClick={() => buy("plan", plan.id)}
                >
                  {busy === plan.id ? "Working…" : "Choose plan"}
                </Button>
              ) : null}
            </CardContent>
          </Card>
        ))}
      </div>

      <h2 className="mb-4 mt-10 text-lg font-semibold">Credit packs</h2>
      <div className="grid gap-4 md:grid-cols-3">
        {packs.map((pack) => (
          <Card key={pack.id}>
            <CardHeader>
              <CardTitle>{pack.name}</CardTitle>
              <CardDescription>{money(pack.price_cents, pack.currency)}</CardDescription>
            </CardHeader>
            <CardContent>
              {canBuy ? (
                <Button className="w-full" disabled={busy === pack.id} onClick={() => buy("pack", pack.id)}>
                  {busy === pack.id ? "Working…" : `Buy ${pack.credits} credits`}
                </Button>
              ) : (
                <p className="text-sm text-muted-foreground">Ask an admin to purchase credits.</p>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      <h2 className="mb-4 mt-10 text-lg font-semibold">Ledger</h2>
      <Card>
        <CardContent className="divide-y p-0">
          {ledger.length === 0 ? (
            <p className="p-6 text-sm text-muted-foreground">No credit movements yet.</p>
          ) : (
            ledger.map((entry) => (
              <div key={entry.id} className="flex items-center justify-between px-6 py-3 text-sm">
                <div>
                  <p>{entry.description}</p>
                  <p className="text-xs text-muted-foreground">
                    {entry.entry_type} · {formatDate(entry.created_at)}
                  </p>
                </div>
                <span className={entry.amount < 0 ? "text-destructive" : ""}>
                  {entry.amount > 0 ? "+" : ""}
                  {entry.amount}
                </span>
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </AppShell>
  );
}
