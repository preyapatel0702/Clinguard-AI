import { useEffect, useRef, useState } from "react";

import type { ChatMessage } from "../../types/chat";
import MessageBubble from "./MessageBubble";
import SuggestedPrompts from "./SuggestedPrompts";

interface MessageListProps {
  messages: ChatMessage[];
  isSending: boolean;
  onRegenerate: () => void;
  onSelectSuggestedPrompt: (prompt: string) => void;
}

const NEAR_BOTTOM_THRESHOLD_PX = 96;

export default function MessageList({
  messages,
  isSending,
  onRegenerate,
  onSelectSuggestedPrompt,
}: MessageListProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const [isPinnedToBottom, setIsPinnedToBottom] = useState(true);

  const handleScroll = () => {
    const el = containerRef.current;
    if (!el) return;
    const distanceFromBottom =
      el.scrollHeight - el.scrollTop - el.clientHeight;
    setIsPinnedToBottom(distanceFromBottom < NEAR_BOTTOM_THRESHOLD_PX);
  };

  useEffect(() => {
    if (isPinnedToBottom) {
      bottomRef.current?.scrollIntoView({ block: "end" });
    }
    // Re-run whenever the message list changes shape or content (e.g.
    // streaming tokens arriving into the last message).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [messages, isSending]);

  const scrollToBottom = () => {
    setIsPinnedToBottom(true);
    bottomRef.current?.scrollIntoView({ block: "end", behavior: "smooth" });
  };

  const lastAssistantId = [...messages]
    .reverse()
    .find((m) => m.role === "assistant")?.id;

  if (messages.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center px-4">
        <SuggestedPrompts onSelect={onSelectSuggestedPrompt} />
      </div>
    );
  }

  return (
    <div className="relative flex-1 min-h-0">
      <div
        ref={containerRef}
        onScroll={handleScroll}
        role="log"
        aria-live="polite"
        aria-relevant="additions"
        className="h-full space-y-5 overflow-y-auto px-1 py-4 sm:px-2"
      >
        {messages.map((message) => (
          <MessageBubble
            key={message.id}
            message={message}
            isLastAssistantMessage={message.id === lastAssistantId}
            onRegenerate={onRegenerate}
            isBusy={isSending}
          />
        ))}
        <div ref={bottomRef} />
      </div>

      {!isPinnedToBottom && (
        <button
          type="button"
          onClick={scrollToBottom}
          className="absolute bottom-3 left-1/2 -translate-x-1/2 rounded-full border border-gray-200 bg-white px-3 py-1.5 text-theme-xs font-medium text-gray-600 shadow-theme-md hover:bg-gray-50 dark:border-gray-800 dark:bg-gray-900 dark:text-gray-300 dark:hover:bg-white/10"
        >
          Scroll to latest ↓
        </button>
      )}
    </div>
  );
}
