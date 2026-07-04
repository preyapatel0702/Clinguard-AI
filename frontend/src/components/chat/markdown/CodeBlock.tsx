import { useState } from "react";

interface CodeBlockProps {
  code: string;
  language?: string;
}

export default function CodeBlock({ code, language }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard API unavailable (unsupported browser / permissions) —
      // fail silently rather than surfacing an error for a non-critical
      // convenience action.
    }
  };

  return (
    <div className="my-3 overflow-hidden rounded-lg border border-gray-200 bg-gray-50 dark:border-gray-800 dark:bg-gray-950">
      <div className="flex items-center justify-between border-b border-gray-200 bg-gray-100 px-3 py-1.5 dark:border-gray-800 dark:bg-white/[0.03]">
        <span className="font-mono text-theme-xs text-gray-500 dark:text-gray-400">
          {language || "text"}
        </span>
        <button
          type="button"
          onClick={handleCopy}
          className="rounded px-2 py-1 text-theme-xs font-medium text-gray-500 hover:bg-gray-200 hover:text-gray-700 dark:text-gray-400 dark:hover:bg-white/10 dark:hover:text-white"
          aria-label={copied ? "Code copied" : "Copy code"}
        >
          {copied ? "Copied" : "Copy"}
        </button>
      </div>
      <pre className="overflow-x-auto p-3 text-theme-xs leading-relaxed">
        <code className="font-mono text-gray-800 dark:text-white/90">
          {code}
        </code>
      </pre>
    </div>
  );
}
