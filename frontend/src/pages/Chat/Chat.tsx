import { useMemo, useState } from "react";

import {
  ChatErrorBanner,
  ChatHeader,
  ChatInput,
  ChatSidebar,
  MessageList,
} from "../../components/chat";
import PageMeta from "../../components/common/PageMeta";
import { useChat } from "../../hooks/useChat";
import { toSummary } from "../../services/chat";

export default function Chat() {
  const {
    conversations,
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
  } = useChat();

  const [isHistoryOpen, setIsHistoryOpen] = useState(false);

  const conversationSummaries = useMemo(
    () => conversations.map(toSummary),
    [conversations]
  );

  const handleSelect = (id: string) => {
    selectConversation(id);
    setIsHistoryOpen(false);
  };

  const handleNewChat = () => {
    newConversation();
    setIsHistoryOpen(false);
  };

  return (
    <>
      <PageMeta
        title="Chat | ClinGuard-AI"
        description="Ask the ClinGuard-AI assistant about audit events, model monitoring, and pipeline runs."
      />

      <div className="flex h-[calc(100vh-9.5rem)] min-h-[520px] overflow-hidden rounded-2xl border border-gray-200 bg-white dark:border-gray-800 dark:bg-white/[0.03]">
        <ChatSidebar
          conversations={conversationSummaries}
          activeConversationId={activeConversationId}
          onSelect={handleSelect}
          onNewChat={handleNewChat}
          onDelete={deleteConversation}
          onClearActive={clearActiveConversation}
          isOpen={isHistoryOpen}
          onClose={() => setIsHistoryOpen(false)}
        />

        <div className="flex min-w-0 flex-1 flex-col">
          <ChatHeader
            title={activeConversation?.title ?? "New chat"}
            onOpenHistory={() => setIsHistoryOpen(true)}
          />

          <div className="flex min-h-0 flex-1 flex-col px-3 sm:px-4">
            <MessageList
              messages={activeConversation?.messages ?? []}
              isSending={isSending}
              onRegenerate={regenerateLastResponse}
              onSelectSuggestedPrompt={sendMessage}
            />

            <div className="pb-3 sm:pb-4">
              {sendError && (
                <ChatErrorBanner
                  message={sendError}
                  onDismiss={dismissSendError}
                />
              )}
              <ChatInput onSend={sendMessage} disabled={isSending} />
              <p className="mt-1.5 px-1 text-theme-xs text-gray-400 dark:text-gray-500">
                ClinGuard-AI can make mistakes. Verify important compliance
                decisions against the audit log.
              </p>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
