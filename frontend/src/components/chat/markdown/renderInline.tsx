import type { ReactNode } from "react";

// Matches, in priority order: inline code, bold+italic, bold, underline
// bold, italic, underline italic, and links. Each alternative uses its own
// capture group so the match branch can be identified by which group is
// defined.
const INLINE_RE =
  /`([^`]+)`|\*\*\*([^*]+)\*\*\*|\*\*([^*]+)\*\*|__([^_]+)__|\*([^*]+)\*|_([^_]+)_|\[([^\]]+)\]\(([^)\s]+)\)/;

export function renderInline(text: string, keyPrefix: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  let remaining = text;
  let index = 0;

  while (remaining.length > 0) {
    const match = INLINE_RE.exec(remaining);
    if (!match) {
      nodes.push(remaining);
      break;
    }

    const before = remaining.slice(0, match.index);
    if (before) nodes.push(before);

    const key = `${keyPrefix}-${index++}`;

    if (match[1] !== undefined) {
      nodes.push(
        <code
          key={key}
          className="rounded bg-gray-100 px-1.5 py-0.5 font-mono text-[0.85em] text-gray-700 dark:bg-white/10 dark:text-white/90"
        >
          {match[1]}
        </code>
      );
    } else if (match[2] !== undefined) {
      nodes.push(
        <strong key={key} className="font-semibold">
          <em>{renderInline(match[2], key)}</em>
        </strong>
      );
    } else if (match[3] !== undefined || match[4] !== undefined) {
      const inner = match[3] ?? match[4];
      nodes.push(
        <strong key={key} className="font-semibold">
          {renderInline(inner, key)}
        </strong>
      );
    } else if (match[5] !== undefined || match[6] !== undefined) {
      const inner = match[5] ?? match[6];
      nodes.push(<em key={key}>{renderInline(inner, key)}</em>);
    } else if (match[7] !== undefined && match[8] !== undefined) {
      nodes.push(
        <a
          key={key}
          href={match[8]}
          target="_blank"
          rel="noreferrer"
          className="font-medium text-brand-500 underline decoration-brand-500/30 underline-offset-2 hover:text-brand-600"
        >
          {match[7]}
        </a>
      );
    }

    remaining = remaining.slice(match.index + match[0].length);
  }

  return nodes;
}

/** Renders inline markdown, preserving single newlines as line breaks. */
export function renderInlineWithBreaks(
  text: string,
  keyPrefix: string
): ReactNode[] {
  const lines = text.split("\n");
  const nodes: ReactNode[] = [];

  lines.forEach((line, i) => {
    if (i > 0) nodes.push(<br key={`${keyPrefix}-br-${i}`} />);
    nodes.push(...renderInline(line, `${keyPrefix}-${i}`));
  });

  return nodes;
}
