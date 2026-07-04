// Shared domain types for the ClinGuard-AI Chat module.
// Mirrors the conventions in `src/types/index.ts`: components and hooks are
// written against these shapes, and the `services/chat` layer is
// responsible for producing data that conforms to them, whether that data
// comes from local mock generation or a real backend.

export type ChatRole = "user" | "assistant";

export type ChatMessageStatus =
  | "sending" // optimistic user message, not yet acknowledged
  | "streaming" // assistant reply actively being generated
  | "complete" // finished, normal message
  | "error"; // failed to send / generate

export interface ChatMessage {
  id: string;
  conversationId: string;
  role: ChatRole;
  content: string;
  createdAt: string; // ISO 8601
  status: ChatMessageStatus;
  /** Present when status === "error"; human-readable failure reason. */
  errorMessage?: string;
}

export interface ChatConversation {
  id: string;
  title: string;
  createdAt: string; // ISO 8601
  updatedAt: string; // ISO 8601
  messages: ChatMessage[];
}

/** Lightweight projection used for the conversation list / sidebar. */
export interface ChatConversationSummary {
  id: string;
  title: string;
  updatedAt: string;
  lastMessagePreview: string;
  messageCount: number;
}

export interface SuggestedPrompt {
  id: string;
  label: string;
  prompt: string;
}

/* ------------------------------------------------------------------ */
/*  Service / API layer                                                */
/* ------------------------------------------------------------------ */

export interface SendChatMessageRequest {
  conversationId: string;
  /** The new user message being sent. */
  message: string;
  /** Prior messages in the conversation, for context. */
  history: ChatMessage[];
}

export interface SendChatMessageResult {
  message: ChatMessage;
}

export type ChatServiceErrorKind =
  | "network" // fetch failed / offline / DNS, etc.
  | "server" // non-2xx response from the API
  | "aborted" // request was cancelled (e.g. regenerate / unmount)
  | "unknown";

/** Domain-specific error thrown by the chat service layer. */
export class ChatServiceError extends Error {
  readonly kind: ChatServiceErrorKind;
  readonly status?: number;

  constructor(message: string, kind: ChatServiceErrorKind, status?: number) {
    super(message);
    this.name = "ChatServiceError";
    this.kind = kind;
    this.status = status;
  }
}
