// Small, dependency-free Markdown parser tailored to assistant chat
// output: headings, paragraphs, fenced code blocks, GFM-style pipe
// tables, ordered/unordered lists, blockquotes, and a horizontal rule,
// plus inline emphasis/code/links. It intentionally doesn't aim for full
// CommonMark coverage (no nested lists, no HTML passthrough) — that scope
// isn't needed for rendering typical LLM responses, and staying dependency
// free avoids adding a package install to the project.

export type TableAlignment = "left" | "center" | "right" | null;

export type MarkdownBlock =
  | { type: "heading"; level: number; text: string }
  | { type: "paragraph"; text: string }
  | { type: "code"; language?: string; code: string }
  | { type: "list"; ordered: boolean; items: string[] }
  | { type: "table"; headers: string[]; rows: string[][]; alignments: TableAlignment[] }
  | { type: "blockquote"; text: string }
  | { type: "hr" };

const FENCE_RE = /^```\s*([\w+-]*)\s*$/;
const HEADING_RE = /^(#{1,6})\s+(.*)$/;
const HR_RE = /^(-{3,}|\*{3,}|_{3,})$/;
const QUOTE_RE = /^>\s?/;
const UL_RE = /^\s*([-*+])\s+(.*)$/;
const OL_RE = /^\s*(\d+)\.\s+(.*)$/;

function splitTableRow(line: string): string[] {
  let trimmed = line.trim();
  if (trimmed.startsWith("|")) trimmed = trimmed.slice(1);
  if (trimmed.endsWith("|")) trimmed = trimmed.slice(0, -1);
  return trimmed.split("|").map((cell) => cell.trim());
}

function isTableSeparatorRow(line: string): boolean {
  if (!line.includes("-") || !line.includes("|")) return false;
  const cells = splitTableRow(line);
  return cells.length > 0 && cells.every((cell) => /^:?-+:?$/.test(cell));
}

function toAlignment(cell: string): TableAlignment {
  const left = cell.startsWith(":");
  const right = cell.endsWith(":");
  if (left && right) return "center";
  if (right) return "right";
  if (left) return "left";
  return null;
}

export function parseMarkdown(markdown: string): MarkdownBlock[] {
  const lines = markdown.replace(/\r\n/g, "\n").split("\n");
  const blocks: MarkdownBlock[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    if (line.trim() === "") {
      i++;
      continue;
    }

    const fenceMatch = FENCE_RE.exec(line.trim());
    if (fenceMatch) {
      const language = fenceMatch[1] || undefined;
      const codeLines: string[] = [];
      i++;
      while (i < lines.length && lines[i].trim() !== "```") {
        codeLines.push(lines[i]);
        i++;
      }
      i++; // consume closing fence (or EOF if unterminated)
      blocks.push({ type: "code", language, code: codeLines.join("\n") });
      continue;
    }

    const headingMatch = HEADING_RE.exec(line);
    if (headingMatch) {
      blocks.push({
        type: "heading",
        level: headingMatch[1].length,
        text: headingMatch[2].trim(),
      });
      i++;
      continue;
    }

    if (HR_RE.test(line.trim())) {
      blocks.push({ type: "hr" });
      i++;
      continue;
    }

    if (line.includes("|") && i + 1 < lines.length && isTableSeparatorRow(lines[i + 1])) {
      const headers = splitTableRow(line);
      const alignments = splitTableRow(lines[i + 1]).map(toAlignment);
      i += 2;
      const rows: string[][] = [];
      while (i < lines.length && lines[i].includes("|") && lines[i].trim() !== "") {
        rows.push(splitTableRow(lines[i]));
        i++;
      }
      blocks.push({ type: "table", headers, rows, alignments });
      continue;
    }

    if (QUOTE_RE.test(line)) {
      const quoteLines: string[] = [];
      while (i < lines.length && QUOTE_RE.test(lines[i])) {
        quoteLines.push(lines[i].replace(QUOTE_RE, ""));
        i++;
      }
      blocks.push({ type: "blockquote", text: quoteLines.join("\n") });
      continue;
    }

    const ulMatch = UL_RE.exec(line);
    const olMatch = OL_RE.exec(line);
    if (ulMatch || olMatch) {
      const ordered = Boolean(olMatch);
      const items: string[] = [];
      while (i < lines.length) {
        const match = ordered ? OL_RE.exec(lines[i]) : UL_RE.exec(lines[i]);
        if (!match) break;
        items.push(match[2]);
        i++;
      }
      blocks.push({ type: "list", ordered, items });
      continue;
    }

    const paragraphLines: string[] = [];
    while (
      i < lines.length &&
      lines[i].trim() !== "" &&
      !FENCE_RE.test(lines[i].trim()) &&
      !HEADING_RE.test(lines[i]) &&
      !QUOTE_RE.test(lines[i]) &&
      !UL_RE.test(lines[i]) &&
      !OL_RE.test(lines[i]) &&
      !HR_RE.test(lines[i].trim())
    ) {
      paragraphLines.push(lines[i]);
      i++;
    }
    blocks.push({ type: "paragraph", text: paragraphLines.join("\n") });
  }

  return blocks;
}
