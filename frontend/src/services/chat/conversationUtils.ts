// Pure, framework-free helpers for constructing and deriving chat data.
// Kept separate from `useChat` so they're easy to unit test in isolation
// and reusable from anywhere in the chat module.

import type {
  ChatConversation,
  ChatConversationSummary,
  ChatMessage,
  ChatMessageStatus,
  ChatRole,
} from "../../types/chat";

const MAX_TITLE_LENGTH = 48;

let idCounter = 0;
function nextLocalId(prefix: string): string {
  idCounter += 1;
  return `${prefix}-${Date.now()}-${idCounter}`;
}

export function createConversation(): ChatConversation {
  const now = new Date().toISOString();
  return {
    id: nextLocalId("conv"),
    title: "New chat",
    createdAt: now,
    updatedAt: now,
    messages: [],
  };
}

export function createMessage(
  conversationId: string,
  role: ChatRole,
  content: string,
  status: ChatMessageStatus
): ChatMessage {
  return {
    id: nextLocalId("msg"),
    conversationId,
    role,
    content,
    createdAt: new Date().toISOString(),
    status,
  };
}

/** Derives a short conversation title from its first user message. */
export function deriveTitle(firstUserMessage: string): string {
  const trimmed = firstUserMessage.trim().replace(/\s+/g, " ");
  if (trimmed.length <= MAX_TITLE_LENGTH) return trimmed || "New chat";
  return `${trimmed.slice(0, MAX_TITLE_LENGTH - 1)}\u2026`;
}

export function toSummary(
  conversation: ChatConversation
): ChatConversationSummary {
  const messages = conversation.messages ?? [];
  const lastMessage = messages[messages.length - 1];

  // `content` can be missing/undefined for placeholder ("streaming") messages,
  // or for older/legacy persisted messages that predate the real backend's
  // response shape — optional chaining + a fallback keep this crash-proof.
  const preview = lastMessage?.content?.replace(/\s+/g, " ").trim().slice(0, 120);

  return {
    id: conversation.id,
    title: conversation.title ?? "New chat",
    updatedAt: conversation.updatedAt,
    lastMessagePreview: preview && preview.length > 0 ? preview : "No messages yet",
    messageCount: messages.length,
  };
}

/** Sorts conversations most-recently-updated first, without mutating input. */
export function sortByRecent(
  conversations: ChatConversation[]
): ChatConversation[] {
  return [...conversations].sort(
    (a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
  );
}