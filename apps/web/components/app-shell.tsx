"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useTheme } from "next-themes";
import { useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api, getToken, setToken } from "@/lib/api";
import { useWorkspace } from "@/lib/workspace";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/projects", label: "Projects" },
  { href: "/videos", label: "Videos" },
  { href: "/create", label: "Create Video" },
  { href: "/library", label: "Library" },
  { href: "/templates", label: "Templates" },
  { href: "/billing", label: "Billing" },
  { href: "/settings", label: "Settings" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { theme, setTheme } = useTheme();
  const [ready, setReady] = useState(false);
  const [name, setName] = useState("");
  const { workspaces, workspace, setWorkspaceId, refresh } = useWorkspace();

  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.replace("/login");
      return;
    }
    api
      .me()
      .then(async (user) => {
        setName(user.name);
        await refresh();
        setReady(true);
      })
      .catch(() => {
        setToken(null);
        router.replace("/login");
      });
  }, [router]);

  if (!ready) {
    return (
      <div className="flex min-h-screen items-center justify-center text-sm text-muted-foreground">
        Loading workspace…
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-20 border-b border-border bg-background/90 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-6">
          <div className="flex items-center gap-8">
            <Link href="/dashboard" className="text-sm font-semibold tracking-tight">
              ShortGen
            </Link>
            <nav className="hidden items-center gap-1 md:flex">
              {NAV.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "rounded-md px-3 py-2 text-sm text-muted-foreground transition-colors hover:text-foreground",
                    pathname === item.href && "bg-secondary text-foreground",
                  )}
                >
                  {item.label}
                </Link>
              ))}
            </nav>
          </div>
          <div className="flex items-center gap-2">
            {workspaces.length > 0 ? (
              <select
                aria-label="Workspace"
                className="hidden h-9 max-w-[180px] rounded-md border border-input bg-background px-2 text-sm md:block"
                value={workspace?.id || ""}
                onChange={(event) => setWorkspaceId(event.target.value)}
              >
                {workspaces.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.name}
                  </option>
                ))}
              </select>
            ) : null}
            <span className="hidden text-sm text-muted-foreground sm:inline">{name}</span>
            <Button
              variant="ghost"
              size="icon"
              aria-label="Toggle theme"
              onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            >
              <Sun className="h-4 w-4 dark:hidden" />
              <Moon className="hidden h-4 w-4 dark:block" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setToken(null);
                router.replace("/login");
              }}
            >
              Sign out
            </Button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
    </div>
  );
}
