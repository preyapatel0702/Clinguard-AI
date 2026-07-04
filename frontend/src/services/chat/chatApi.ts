// Chat API integration for ClinGuard-AI.
//
// Every network call goes through `request()` from `api/client.ts` — the
// same seam the rest of the app uses — so there are no hardcoded URLs here.
// The base URL comes from `VITE_API_BASE_URL` and the chat-specific route
// from `VITE_CHAT_ENDPOINT`, both read once at module load.
//
// The chat backend is live, so `sendChatMessage` always calls it — there is
// no local mock fallback here (see the other `services/*Api.ts` modules for
// the same pattern).

import { ApiError, request } from "../../api/client";
import {
  ChatServiceError,
  type ChatMessage,
  type SendChatMessageRequest,
} from "../../types/chat";
import { createMessage } from "./conversationUtils";

const CHAT_ENDPOINT = import.meta.env.VITE_CHAT_ENDPOINT ?? "/chat/messages";

/**
 * Shape returned by the real ClinGuard backend for POST /chat/messages
 * (see `backend/models/chat_schemas.py::ChatResponse`). This intentionally
 * does *not* match the old mock format ({ id, conversationId, content,
 * createdAt }) — the backend returns the assistant text under `reply`, plus
 * safety-analysis metadata that the current UI doesn't render yet. All
 * fields are treated as optional here since they come from across the wire.
 */
interface ChatCompletionApiResponse {
  role?: string;
  reply?: string;
  session_id?: string;
  risk_level?: string;
  risk_score?: number;
  alerts?: unknown[];
  analysis?: Record<string, unknown>;
}

function toChatMessage(
  response: ChatCompletionApiResponse,
  conversationId: string
): ChatMessage {
  // `id`/`createdAt` aren't part of the backend contract, so generate them
  // client-side the same way any other locally-created message is built.
  return createMessage(
    conversationId,
    "assistant",
    response.reply ?? "",
    "complete"
  );
}

/**
 * Sends a user message and resolves with the assistant's reply.
 *
 * Throws `ChatServiceError` on failure, with `kind` set to `"network"`,
 * `"server"`, or `"aborted"` so callers (see `useChat`) can show an
 * appropriate, specific error state instead of a generic failure message.
 */
export async function sendChatMessage(
  payload: SendChatMessageRequest,
  signal?: AbortSignal
): Promise<ChatMessage> {
  try {
    const response = await request<ChatCompletionApiResponse>(
      CHAT_ENDPOINT,
      {
        method: "POST",
        body: {
          // `session_id` is the backend's field name (see ChatRequest);
          // conversationId doubles as the chat session identifier.
          session_id: payload.conversationId,
          message: payload.message,
          messages: [
            ...payload.history.map((message) => ({
              role: message.role,
              content: message.content,
            })),
            { role: "user", content: payload.message },
          ],
        },
        signal,
      }
    );

    return toChatMessage(response, payload.conversationId);
  } catch (error) {
    if (signal?.aborted) {
      throw new ChatServiceError("Request was cancelled.", "aborted");
    }

    if (error instanceof ApiError) {
      throw new ChatServiceError(
        error.status >= 500
          ? "The assistant service is temporarily unavailable. Please try again."
          : "The assistant could not process that message.",
        "server",
        error.status
      );
    }

    throw new ChatServiceError(
      "Unable to reach the assistant service. Check your connection and try again.",
      "network"
    );
  }
}