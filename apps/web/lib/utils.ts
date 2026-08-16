import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—";
  return new Date(value).toLocaleString();
}

export function stageLabel(stage: string | null | undefined): string {
  const labels: Record<string, string> = {
    QUEUED: "Queued",
    ANALYZING: "Analyzing your brief",
    GENERATING_SCRIPT: "Generating script",
    PLANNING: "Planning scenes",
    FETCHING_MEDIA: "Fetching media",
    GENERATING_AUDIO: "Generating audio",
    GENERATING_SUBTITLES: "Generating subtitles",
    RENDERING: "Rendering video",
    UPLOADING: "Uploading result",
    COMPLETED: "Completed",
    FAILED: "Failed",
    CANCELLED: "Cancelled",
  };
  return labels[stage || ""] || stage || "Waiting";
}
