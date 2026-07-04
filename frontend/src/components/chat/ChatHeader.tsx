interface ChatHeaderProps {
  title: string;
  onOpenHistory: () => void;
}

export default function ChatHeader({ title, onOpenHistory }: ChatHeaderProps) {
  return (
    <div className="flex items-center gap-2 border-b border-gray-200 px-4 py-3 dark:border-gray-800">
      <button
        type="button"
        onClick={onOpenHistory}
        aria-label="Open conversation history"
        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-white/10 lg:hidden"
      >
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          aria-hidden="true"
        >
          <path
            d="M4 6H20M4 12H20M4 18H14"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
          />
        </svg>
      </button>
      <h1 className="truncate text-theme-sm font-semibold text-gray-800 dark:text-white/90">
        {title}
      </h1>
    </div>
  );
}
