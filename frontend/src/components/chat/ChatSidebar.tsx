import type { ChatConversationSummary } from "../../types/chat";
import { formatRelativeTime } from "../../utils/format";

interface ChatSidebarProps {
  conversations: ChatConversationSummary[];
  activeConversationId: string | null;
  onSelect: (id: string) => void;
  onNewChat: () => void;
  onDelete: (id: string) => void;
  onClearActive: () => void;
  isOpen: boolean;
  onClose: () => void;
}

export default function ChatSidebar({
  conversations,
  activeConversationId,
  onSelect,
  onNewChat,
  onDelete,
  onClearActive,
  isOpen,
  onClose,
}: ChatSidebarProps) {
  return (
    <>
      {isOpen && (
        <button
          type="button"
          aria-label="Close conversation history"
          onClick={onClose}
          className="fixed inset-0 z-40 bg-gray-900/40 lg:hidden"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-72 shrink-0 flex-col border-r border-gray-200 bg-white p-3 transition-transform duration-200 dark:border-gray-800 dark:bg-gray-900 lg:static lg:z-auto lg:translate-x-0 ${
          isOpen ? "translate-x-0" : "-translate-x-full"
        }`}
        aria-label="Chat history"
      >
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onNewChat}
            className="flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-brand-500 px-3 py-2 text-theme-sm font-medium text-white hover:bg-brand-600"
          >
            <span aria-hidden="true">+</span> New chat
          </button>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close conversation history"
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-white/10 lg:hidden"
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              aria-hidden="true"
            >
              <path
                fillRule="evenodd"
                clipRule="evenodd"
                d="M6.21967 7.28131C5.92678 6.98841 5.92678 6.51354 6.21967 6.22065C6.51256 5.92775 6.98744 5.92775 7.28033 6.22065L11.999 10.9393L16.7176 6.22078C17.0105 5.92789 17.4854 5.92788 17.7782 6.22078C18.0711 6.51367 18.0711 6.98855 17.7782 7.28144L13.0597 12L17.7782 16.7186C18.0711 17.0115 18.0711 17.4863 17.7782 17.7792C17.4854 18.0721 17.0105 18.0721 16.7176 17.7792L11.999 13.0607L7.28033 17.7794C6.98744 18.0722 6.51256 18.0722 6.21967 17.7794C5.92678 17.4865 5.92678 17.0116 6.21967 16.7187L10.9384 12L6.21967 7.28131Z"
                fill="currentColor"
              />
            </svg>
          </button>
        </div>

        <button
          type="button"
          onClick={onClearActive}
          disabled={!activeConversationId}
          className="mt-2 rounded-lg px-3 py-1.5 text-left text-theme-xs font-medium text-gray-500 hover:bg-gray-100 hover:text-gray-700 disabled:cursor-not-allowed disabled:opacity-50 dark:text-gray-400 dark:hover:bg-white/10 dark:hover:text-gray-200"
        >
          Clear current chat
        </button>

        <nav
          aria-label="Conversations"
          className="mt-3 flex-1 space-y-1 overflow-y-auto"
        >
          {conversations.length === 0 ? (
            <p className="px-3 py-4 text-theme-xs text-gray-400 dark:text-gray-500">
              No conversations yet.
            </p>
          ) : (
            conversations.map((conversation) => {
              const isActive = conversation.id === activeConversationId;
              return (
                <div
                  key={conversation.id}
                  className={`group flex items-center gap-1 rounded-lg px-1 ${
                    isActive
                      ? "bg-brand-50 dark:bg-brand-500/15"
                      : "hover:bg-gray-100 dark:hover:bg-white/5"
                  }`}
                >
                  <button
                    type="button"
                    onClick={() => onSelect(conversation.id)}
                    aria-current={isActive ? "true" : undefined}
                    className="min-w-0 flex-1 truncate px-2 py-2 text-left"
                  >
                    <span
                      className={`block truncate text-theme-sm font-medium ${
                        isActive
                          ? "text-brand-600 dark:text-brand-400"
                          : "text-gray-700 dark:text-gray-200"
                      }`}
                    >
                      {conversation.title}
                    </span>
                    <span className="block truncate text-theme-xs text-gray-400 dark:text-gray-500">
                      {formatRelativeTime(conversation.updatedAt)}
                    </span>
                  </button>
                  <button
                    type="button"
                    onClick={() => onDelete(conversation.id)}
                    aria-label={`Delete conversation "${conversation.title}"`}
                    className="shrink-0 rounded p-1.5 text-gray-400 opacity-0 hover:bg-gray-200 hover:text-error-500 focus:opacity-100 group-hover:opacity-100 dark:hover:bg-white/10"
                  >
                    <svg
                      width="14"
                      height="14"
                      viewBox="0 0 24 24"
                      fill="none"
                      xmlns="http://www.w3.org/2000/svg"
                      aria-hidden="true"
                    >
                      <path
                        d="M6 6L18 18M18 6L6 18"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                      />
                    </svg>
                  </button>
                </div>
              );
            })
          )}
        </nav>
      </aside>
    </>
  );
}
