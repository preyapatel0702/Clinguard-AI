import { useEffect, useRef, useState } from "react";
import type { KeyboardEvent } from "react";

interface ChatInputProps {
  onSend: (content: string) => void;
  disabled?: boolean;
}

const MAX_TEXTAREA_HEIGHT_PX = 200;

export default function ChatInput({ onSend, disabled = false }: ChatInputProps) {
  const [value, setValue] = useState("");
  const [isComposing, setIsComposing] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, MAX_TEXTAREA_HEIGHT_PX)}px`;
  }, [value]);

  const submit = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey && !isComposing) {
      event.preventDefault();
      submit();
    }
  };

  return (
    <form
      className="flex items-end gap-2 rounded-xl border border-gray-200 bg-white p-2 shadow-theme-xs focus-within:border-brand-300 focus-within:ring-3 focus-within:ring-brand-500/10 dark:border-gray-800 dark:bg-white/[0.03] dark:focus-within:border-brand-800"
      onSubmit={(event) => {
        event.preventDefault();
        submit();
      }}
    >
      <label htmlFor="chat-message-input" className="sr-only">
        Message the ClinGuard-AI assistant
      </label>
      <textarea
        id="chat-message-input"
        ref={textareaRef}
        rows={1}
        value={value}
        disabled={disabled}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={handleKeyDown}
        onCompositionStart={() => setIsComposing(true)}
        onCompositionEnd={() => setIsComposing(false)}
        placeholder="Message the ClinGuard-AI assistant… (Enter to send, Shift+Enter for a new line)"
        className="max-h-[200px] flex-1 resize-none bg-transparent px-2 py-2 text-theme-sm text-gray-800 placeholder:text-gray-400 outline-hidden disabled:cursor-not-allowed disabled:opacity-60 dark:text-white/90 dark:placeholder:text-white/30"
      />
      <button
        type="submit"
        disabled={disabled || value.trim().length === 0}
        aria-label="Send message"
        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-brand-500 text-white transition hover:bg-brand-600 disabled:cursor-not-allowed disabled:bg-gray-200 disabled:text-gray-400 dark:disabled:bg-white/10 dark:disabled:text-gray-600"
      >
        <svg
          width="18"
          height="18"
          viewBox="0 0 20 20"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
        >
          <path
            d="M17.5 2.5L2.5 8.33333L9.16667 10.8333M17.5 2.5L11.6667 17.5L9.16667 10.8333M17.5 2.5L9.16667 10.8333"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </button>
    </form>
  );
}
