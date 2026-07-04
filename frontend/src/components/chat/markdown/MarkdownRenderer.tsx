import { createElement, Fragment } from "react";

import CodeBlock from "./CodeBlock";
import { parseMarkdown, type TableAlignment } from "./parseMarkdown";
import { renderInline, renderInlineWithBreaks } from "./renderInline";

interface MarkdownRendererProps {
  content: string;
}

const HEADING_CLASSES: Record<number, string> = {
  1: "text-theme-xl font-semibold",
  2: "text-lg font-semibold",
  3: "text-base font-semibold",
  4: "text-base font-medium",
  5: "text-sm font-medium",
  6: "text-sm font-medium",
};

function alignClass(alignment: TableAlignment): string {
  if (alignment === "center") return "text-center";
  if (alignment === "right") return "text-right";
  return "text-left";
}

export default function MarkdownRenderer({ content }: MarkdownRendererProps) {
  const blocks = parseMarkdown(content);

  return (
    <div className="space-y-3 text-theme-sm leading-relaxed break-words">
      {blocks.map((block, blockIndex) => {
        const key = `block-${blockIndex}`;

        switch (block.type) {
          case "heading": {
            const level = Math.min(Math.max(block.level, 1), 6);
            return createElement(
              `h${level}`,
              {
                key,
                className: `${HEADING_CLASSES[level]} text-gray-800 dark:text-white/90`,
              },
              renderInline(block.text, key)
            );
          }

          case "paragraph":
            return (
              <p key={key} className="text-gray-700 dark:text-gray-300">
                {renderInlineWithBreaks(block.text, key)}
              </p>
            );

          case "code":
            return (
              <CodeBlock key={key} code={block.code} language={block.language} />
            );

          case "list": {
            const ListTag = block.ordered ? "ol" : "ul";
            return (
              <ListTag
                key={key}
                className={`ml-5 space-y-1 text-gray-700 dark:text-gray-300 ${
                  block.ordered ? "list-decimal" : "list-disc"
                }`}
              >
                {block.items.map((item, itemIndex) => (
                  <li key={`${key}-item-${itemIndex}`}>
                    {renderInline(item, `${key}-item-${itemIndex}`)}
                  </li>
                ))}
              </ListTag>
            );
          }

          case "table":
            return (
              <div
                key={key}
                className="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-800"
              >
                <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-800">
                  <thead className="bg-gray-50 dark:bg-white/[0.03]">
                    <tr>
                      {block.headers.map((header, colIndex) => (
                        <th
                          key={`${key}-h-${colIndex}`}
                          scope="col"
                          className={`whitespace-nowrap px-3 py-2 text-theme-xs font-semibold text-gray-600 dark:text-gray-300 ${alignClass(
                            block.alignments[colIndex] ?? null
                          )}`}
                        >
                          {renderInline(header, `${key}-h-${colIndex}`)}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
                    {block.rows.map((row, rowIndex) => (
                      <tr key={`${key}-r-${rowIndex}`}>
                        {row.map((cell, colIndex) => (
                          <td
                            key={`${key}-r-${rowIndex}-c-${colIndex}`}
                            className={`px-3 py-2 text-gray-700 dark:text-gray-300 ${alignClass(
                              block.alignments[colIndex] ?? null
                            )}`}
                          >
                            {renderInline(cell, `${key}-r-${rowIndex}-c-${colIndex}`)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            );

          case "blockquote":
            return (
              <blockquote
                key={key}
                className="border-l-2 border-brand-300 pl-3 text-gray-600 italic dark:border-brand-700 dark:text-gray-400"
              >
                {renderInlineWithBreaks(block.text, key)}
              </blockquote>
            );

          case "hr":
            return (
              <hr key={key} className="border-gray-200 dark:border-gray-800" />
            );

          default:
            return <Fragment key={key} />;
        }
      })}
    </div>
  );
}
