import type { Metadata } from "next";
import { ThemeProvider } from "@/components/theme-provider";
import { WorkspaceProvider } from "@/lib/workspace";
import "./globals.css";

export const metadata: Metadata = {
  title: "ShortGen — AI Video Studio",
  description: "Create short-form videos from a topic. Multi-tenant AI video SaaS.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body>
        <ThemeProvider>
          <WorkspaceProvider>{children}</WorkspaceProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
