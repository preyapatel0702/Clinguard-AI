// Local persistence for chat conversations.
//
// There is no backend conversation store yet, so conversation history is
// kept in `localStorage` on the client. Everything routes through the two
// functions below, so swapping this for a real API-backed store later
// (e.g. `GET/PUT /chat/conversations`) only requires changing this file —
// `useChat` and every component are written against `ChatConversation[]`
// and don't know or care where it comes from.

import type {
  ChatConversation,
  ChatMessage,
  ChatMessageStatus,
  ChatRole,
} from "../../types/chat";

const STORAGE_KEY = "clinguard.chat.conversations.v1";

const VALID_ROLES: ChatRole[] = ["user", "assistant"];
const VALID_STATUSES: ChatMessageStatus[] = [
  "sending",
  "streaming",
  "complete",
  "error",
];

let fallbackIdCounter = 0;
/** Local id generator for records that are missing one during migration. */
function fallbackId(prefix: string): string {
  fallbackIdCounter += 1;
  return `${prefix}-migrated-${Date.now()}-${fallbackIdCounter}`;
}

/**
 * Normalizes a single persisted message into the current `ChatMessage`
 * shape. Handles data written by older builds — e.g. messages saved before
 * the real backend integration, which could be missing `content` (or carry
 * it under a different key) — so a stale localStorage entry can't crash the
 * chat UI (see `conversationUtils.ts::toSummary`).
 */
function migrateMessage(raw: unknown, conversationId: string): ChatMessage | null {
  if (typeof raw !== "object" || raw === null) return null;
  const candidate = raw as Record<string, unknown>;

  const role: ChatRole = VALID_ROLES.includes(candidate.role as ChatRole)
    ? (candidate.role as ChatRole)
    : "assistant";

  const status: ChatMessageStatus = VALID_STATUSES.includes(
    candidate.status as ChatMessageStatus
  )
    ? (candidate.status as ChatMessageStatus)
    : "complete";

  // Legacy/mock payloads have been observed storing the reply text under
  // `content`, `text`, or `message` — normalize whichever is present, and
  // fall back to an empty string rather than `undefined`.
  const rawContent = candidate.content ?? candidate.text ?? candidate.message;
  const content = typeof rawContent === "string" ? rawContent : "";

  const message: ChatMessage = {
    id: typeof candidate.id === "string" && candidate.id ? candidate.id : fallbackId("msg"),
    conversationId:
      typeof candidate.conversationId === "string" && candidate.conversationId
        ? candidate.conversationId
        : conversationId,
    role,
    content,
    createdAt:
      typeof candidate.createdAt === "string" && candidate.createdAt
        ? candidate.createdAt
        : new Date().toISOString(),
    status,
  };

  if (typeof candidate.errorMessage === "string") {
    message.errorMessage = candidate.errorMessage;
  }

  return message;
}

/**
 * Normalizes a single persisted conversation, migrating its messages and
 * filling in any missing required fields. Returns `null` only when the
 * record is unusable (no id), so it can be dropped without affecting the
 * rest of the user's history.
 */
function migrateConversation(raw: unknown): ChatConversation | null {
  if (typeof raw !== "object" || raw === null) return null;
  const candidate = raw as Record<string, unknown>;

  if (typeof candidate.id !== "string" || !candidate.id) return null;

  const now = new Date().toISOString();
  const messages = Array.isArray(candidate.messages)
    ? candidate.messages
        .map((message) => migrateMessage(message, candidate.id as string))
        .filter((message): message is ChatMessage => message !== null)
    : [];

  return {
    id: candidate.id,
    title:
      typeof candidate.title === "string" && candidate.title
        ? candidate.title
        : "New chat",
    createdAt:
      typeof candidate.createdAt === "string" && candidate.createdAt
        ? candidate.createdAt
        : now,
    updatedAt:
      typeof candidate.updatedAt === "string" && candidate.updatedAt
        ? candidate.updatedAt
        : now,
    messages,
  };
}

/**
 * Reads persisted conversations, migrating any legacy/malformed entries
 * (e.g. from the old mock response format) into the current shape rather
 * than dropping them. Never throws; returns [] on any failure.
 */
export function loadConversations(): ChatConversation[] {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];

    const parsed: unknown = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];

    const migrated = parsed
      .map(migrateConversation)
      .filter((conversation): conversation is ChatConversation => conversation !== null);

    // Persist the migrated shape so we only pay the migration cost once.
    if (raw !== JSON.stringify(migrated)) {
      saveConversations(migrated);
    }

    return migrated;
  } catch {
    // Corrupt data, storage disabled (private browsing), or unavailable
    // (SSR-like context). Fail safe with an empty history rather than
    // throwing during app startup.
    return [];
  }
}

/** Persists conversations. Failures are swallowed (e.g. quota exceeded). */
export function saveConversations(conversations: ChatConversation[]): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations));
  } catch {
    // Non-fatal: the conversation still lives in memory for this session.
  }
}