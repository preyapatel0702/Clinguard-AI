import type { SuggestedPrompt } from "../../types/chat";

export const SUGGESTED_PROMPTS: SuggestedPrompt[] = [
  {
    id: "compliance-summary",
    label: "Summarize today's compliance status",
    prompt:
      "Summarize today's compliance status across audit, monitoring, and pipelines.",
  },
  {
    id: "model-drift",
    label: "Explain a model drift alert",
    prompt:
      "Compare the current model fleet and flag anything with elevated drift.",
  },
  {
    id: "audit-query",
    label: "Write a query for flagged audit events",
    prompt: "Write a query to pull flagged audit events from the last 24 hours.",
  },
  {
    id: "release-checklist",
    label: "Draft a compliant release checklist",
    prompt: "Draft a checklist for a HIPAA-aligned model release.",
  },
];
