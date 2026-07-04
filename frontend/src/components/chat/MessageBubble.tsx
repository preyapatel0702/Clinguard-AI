import { useState } from "react";

import type { ChatMessage } from "../../types/chat";
import { formatRelativeTime } from "../../utils/format";
import MarkdownRenderer from "./markdown/MarkdownRenderer";
import TypingIndicator from "./TypingIndicator";

interface MessageBubbleProps {
  message: ChatMessage;
  isLastAssistantMessage?: boolean;
  onRegenerate?: () => void;
  isBusy?: boolean;
}

export default function MessageBubble({
  message,
  isLastAssistantMessage = false,
  onRegenerate,
  isBusy = false,
}: MessageBubbleProps) {
  const [copied, setCopied] = useState(false);
  const isUser = message.role === "user";

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      // Non-critical convenience action; ignore clipboard failures.
    }
  };

  const isEmptyStreaming = message.status === "streaming" && !message.content;

  return (
    <div
      className={`group flex gap-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}
    >
      <div
        className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-theme-xs font-semibold ${
          isUser
            ? "bg-brand-500 text-white"
            : "bg-gray-100 text-gray-600 dark:bg-white/10 dark:text-gray-300"
        }`}
        aria-hidden="true"
      >
        {isUser ? "You" : "AI"}
      </div>

      <div
        className={`flex max-w-[85%] flex-col gap-1 sm:max-w-[75%] ${
          isUser ? "items-end" : "items-start"
        }`}
      >
        <div
          className={`rounded-2xl px-4 py-2.5 ${
            isUser
              ? "bg-brand-500 text-white"
              : message.status === "error"
              ? "border border-error-200 bg-error-50 dark:border-error-500/30 dark:bg-error-500/10"
              : "border border-gray-200 bg-white dark:border-gray-800 dark:bg-white/[0.03]"
          }`}
        >
          {isEmptyStreaming ? (
            <TypingIndicator />
          ) : isUser ? (
            <p className="whitespace-pre-wrap text-theme-sm leading-relaxed">
              {message.content}
            </p>
          ) : (
            <MarkdownRenderer content={message.content} />
          )}

          {message.status === "error" && (
            <p className="mt-2 flex items-center gap-1 text-theme-xs font-medium text-error-600 dark:text-error-400">
              {message.errorMessage ?? "Something went wrong."}
            </p>
          )}
        </div>

        <div
          className={`flex items-center gap-2 px-1 text-theme-xs text-gray-400 opacity-0 transition-opacity group-hover:opacity-100 dark:text-gray-500 ${
            isBusy ? "" : "focus-within:opacity-100"
          }`}
        >
          <span aria-hidden="true">{formatRelativeTime(message.createdAt)}</span>

          {!isEmptyStreaming && message.content && (
            <button
              type="button"
              onClick={handleCopy}
              className="rounded px-1.5 py-0.5 font-medium hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-white/10 dark:hover:text-gray-300"
              aria-label="Copy message"
            >
              {copied ? "Copied" : "Copy"}
            </button>
          )}

          {!isUser && isLastAssistantMessage && onRegenerate && !isEmptyStreaming && (
            <button
              type="button"
              onClick={onRegenerate}
              disabled={isBusy}
              className="rounded px-1.5 py-0.5 font-medium hover:bg-gray-100 hover:text-gray-600 disabled:cursor-not-allowed disabled:opacity-50 dark:hover:bg-white/10 dark:hover:text-gray-300"
              aria-label="Regenerate response"
            >
              Regenerate
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
