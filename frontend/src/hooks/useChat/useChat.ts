import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  createConversation,
  createMessage,
  deriveTitle,
  loadConversations,
  saveConversations,
  sendChatMessage,
  sortByRecent,
} from "../../services/chat";
import {
  ChatServiceError,
  type ChatConversation,
  type ChatMessage,
} from "../../types/chat";

export interface UseChatResult {
  conversations: ChatConversation[];
  activeConversation: ChatConversation | undefined;
  activeConversationId: string | null;
  isSending: boolean;
  sendError: string | null;
  selectConversation: (id: string) => void;
  newConversation: () => void;
  clearActiveConversation: () => void;
  deleteConversation: (id: string) => void;
  sendMessage: (content: string) => Promise<void>;
  regenerateLastResponse: () => Promise<void>;
  dismissSendError: () => void;
}

function withConversation(
  conversations: ChatConversation[],
  id: string,
  updater: (conversation: ChatConversation) => ChatConversation
): ChatConversation[] {
  return conversations.map((conversation) =>
    conversation.id === id ? updater(conversation) : conversation
  );
}

export function useChat(): UseChatResult {
  const [conversations, setConversations] = useState<ChatConversation[]>(
    () => {
      const stored = loadConversations();
      return stored.length > 0 ? sortByRecent(stored) : [createConversation()];
    }
  );
  const [activeConversationId, setActiveConversationId] = useState<
    string | null
  >(() => conversations[0]?.id ?? null);
  const [isSending, setIsSending] = useState(false);
  const [sendError, setSendError] = useState<string | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);

  // Persist on every change. Cheap for localStorage at this scale, and
  // keeps the "swap in a real API later" seam (chatStorage.ts) simple.
  useEffect(() => {
    saveConversations(conversations);
  }, [conversations]);

  // Cancel any in-flight request if the component unmounts mid-send.
  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  const activeConversation = useMemo(
    () => conversations.find((c) => c.id === activeConversationId),
    [conversations, activeConversationId]
  );

  const selectConversation = useCallback((id: string) => {
    abortControllerRef.current?.abort();
    setIsSending(false);
    setSendError(null);
    setActiveConversationId(id);
  }, []);

  const newConversation = useCallback(() => {
    abortControllerRef.current?.abort();
    setIsSending(false);
    setSendError(null);

    const conversation = createConversation();
    setConversations((prev) => [conversation, ...prev]);
    setActiveConversationId(conversation.id);
  }, []);

  const clearActiveConversation = useCallback(() => {
    if (!activeConversationId) return;
    abortControllerRef.current?.abort();
    setIsSending(false);
    setSendError(null);

    setConversations((prev) =>
      withConversation(prev, activeConversationId, (conversation) => ({
        ...conversation,
        title: "New chat",
        messages: [],
        updatedAt: new Date().toISOString(),
      }))
    );
  }, [activeConversationId]);

  const deleteConversation = useCallback(
    (id: string) => {
      setConversations((prev) => {
        const remaining = prev.filter((c) => c.id !== id);
        const next = remaining.length > 0 ? remaining : [createConversation()];

        if (id === activeConversationId) {
          abortControllerRef.current?.abort();
          setIsSending(false);
          setSendError(null);
          setActiveConversationId(sortByRecent(next)[0].id);
        }

        return next;
      });
    },
    [activeConversationId]
  );

  const dismissSendError = useCallback(() => setSendError(null), []);

  /**
   * Shared core: appends a user message (unless `retryUserMessage` reuses
   * an existing one for regeneration), calls the chat service, and
   * reconciles the resulting assistant message into state.
   */
  const runSend = useCallback(
    async (conversationId: string, userMessage: ChatMessage, history: ChatMessage[]) => {
      const controller = new AbortController();
      abortControllerRef.current = controller;
      setIsSending(true);
      setSendError(null);

      const placeholder = createMessage(
        conversationId,
        "assistant",
        "",
        "streaming"
      );

      setConversations((prev) =>
        withConversation(prev, conversationId, (conversation) => ({
          ...conversation,
          messages: [...conversation.messages, placeholder],
          updatedAt: new Date().toISOString(),
        }))
      );

      try {
        const reply = await sendChatMessage(
          { conversationId, message: userMessage.content, history },
          controller.signal
        );

        setConversations((prev) =>
          withConversation(prev, conversationId, (conversation) => ({
            ...conversation,
            messages: conversation.messages.map((message) =>
              message.id === placeholder.id
                ? { ...reply, id: placeholder.id }
                : message
            ),
            updatedAt: new Date().toISOString(),
          }))
        );
      } catch (error) {
        const serviceError =
          error instanceof ChatServiceError
            ? error
            : new ChatServiceError("Something went wrong.", "unknown");

        if (serviceError.kind === "aborted") {
          // Cancelled deliberately (new send, switched conversation, or
          // unmount) — remove the placeholder rather than showing an error.
          setConversations((prev) =>
            withConversation(prev, conversationId, (conversation) => ({
              ...conversation,
              messages: conversation.messages.filter(
                (message) => message.id !== placeholder.id
              ),
            }))
          );
          return;
        }

        setSendError(serviceError.message);
        setConversations((prev) =>
          withConversation(prev, conversationId, (conversation) => ({
            ...conversation,
            messages: conversation.messages.map((message) =>
              message.id === placeholder.id
                ? {
                    ...message,
                    status: "error",
                    errorMessage: serviceError.message,
                  }
                : message
            ),
          }))
        );
      } finally {
        setIsSending(false);
        if (abortControllerRef.current === controller) {
          abortControllerRef.current = null;
        }
      }
    },
    []
  );

  const sendMessage = useCallback(
    async (content: string) => {
      const trimmed = content.trim();
      if (!trimmed || isSending) return;

      const conversation = activeConversation ?? conversations[0];
      if (!conversation) return;

      const userMessage = createMessage(
        conversation.id,
        "user",
        trimmed,
        "complete"
      );
      const history = conversation.messages.filter(
        (message) => message.status === "complete"
      );
      const isFirstMessage = conversation.messages.length === 0;

      setConversations((prev) =>
        withConversation(prev, conversation.id, (c) => ({
          ...c,
          title: isFirstMessage ? deriveTitle(trimmed) : c.title,
          messages: [...c.messages, userMessage],
          updatedAt: new Date().toISOString(),
        }))
      );

      await runSend(conversation.id, userMessage, history);
    },
    [activeConversation, conversations, isSending, runSend]
  );

  const regenerateLastResponse = useCallback(async () => {
    if (!activeConversation || isSending) return;

    const messages = activeConversation.messages;
    const lastAssistantIndex = [...messages]
      .map((m, i) => ({ m, i }))
      .reverse()
      .find(({ m }) => m.role === "assistant")?.i;

    if (lastAssistantIndex === undefined) return;

    const lastUserMessage = [...messages.slice(0, lastAssistantIndex)]
      .reverse()
      .find((m) => m.role === "user");

    if (!lastUserMessage) return;

    const history = messages
      .slice(0, lastAssistantIndex)
      .filter((message) => message.status === "complete");

    setConversations((prev) =>
      withConversation(prev, activeConversation.id, (conversation) => ({
        ...conversation,
        messages: conversation.messages.slice(0, lastAssistantIndex),
      }))
    );

    await runSend(activeConversation.id, lastUserMessage, history);
  }, [activeConversation, isSending, runSend]);

  return {
    conversations: useMemo(() => sortByRecent(conversations), [conversations]),
    activeConversation,
    activeConversationId,
    isSending,
    sendError,
    selectConversation,
    newConversation,
    clearActiveConversation,
    deleteConversation,
    sendMessage,
    regenerateLastResponse,
    dismissSendError,
  };
}
