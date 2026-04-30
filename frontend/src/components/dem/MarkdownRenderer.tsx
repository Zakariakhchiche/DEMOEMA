"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type Props = {
  content: string;
  fontSize?: number;
  className?: string;
};

export function MarkdownRenderer({ content, fontSize = 14, className }: Props) {
  return (
    <div
      className={className}
      style={{
        fontSize,
        lineHeight: 1.55,
        color: "var(--text-primary)",
        wordBreak: "break-word",
        overflowWrap: "anywhere",
      }}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          p: ({ children }) => (
            <p style={{ margin: "0 0 10px 0" }}>{children}</p>
          ),
          a: ({ href, children }) => (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: "var(--accent-blue)", textDecoration: "underline" }}
            >
              {children}
            </a>
          ),
          strong: ({ children }) => (
            <strong style={{ fontWeight: 600, color: "var(--text-primary)" }}>{children}</strong>
          ),
          em: ({ children }) => <em style={{ fontStyle: "italic" }}>{children}</em>,
          code: ({ children, className }) => {
            const isInline = !className;
            if (isInline) {
              return (
                <code
                  style={{
                    background: "rgba(255,255,255,0.06)",
                    padding: "2px 6px",
                    borderRadius: 4,
                    fontSize: "0.9em",
                    fontFamily: "ui-monospace, SFMono-Regular, monospace",
                    color: "var(--accent-purple)",
                  }}
                >
                  {children}
                </code>
              );
            }
            return <code className={className}>{children}</code>;
          },
          pre: ({ children }) => (
            <pre
              style={{
                background: "rgba(255,255,255,0.04)",
                border: "1px solid rgba(255,255,255,0.08)",
                borderRadius: 8,
                padding: 12,
                margin: "10px 0",
                overflow: "auto",
                fontSize: 12.5,
                fontFamily: "ui-monospace, SFMono-Regular, monospace",
              }}
            >
              {children}
            </pre>
          ),
          ul: ({ children }) => (
            <ul style={{ margin: "8px 0", paddingLeft: 24 }}>{children}</ul>
          ),
          ol: ({ children }) => (
            <ol style={{ margin: "8px 0", paddingLeft: 24 }}>{children}</ol>
          ),
          li: ({ children }) => <li style={{ margin: "4px 0" }}>{children}</li>,
          blockquote: ({ children }) => (
            <blockquote
              style={{
                borderLeft: "3px solid var(--accent-purple)",
                paddingLeft: 12,
                margin: "10px 0",
                color: "var(--text-secondary)",
                fontStyle: "italic",
              }}
            >
              {children}
            </blockquote>
          ),
          h1: ({ children }) => (
            <h1 style={{ fontSize: 20, fontWeight: 600, margin: "14px 0 8px" }}>{children}</h1>
          ),
          h2: ({ children }) => (
            <h2 style={{ fontSize: 17, fontWeight: 600, margin: "12px 0 6px" }}>{children}</h2>
          ),
          h3: ({ children }) => (
            <h3 style={{ fontSize: 15, fontWeight: 600, margin: "10px 0 6px" }}>{children}</h3>
          ),
          table: ({ children }) => (
            <div style={{ overflowX: "auto", margin: "10px 0" }}>
              <table
                style={{
                  borderCollapse: "collapse",
                  width: "100%",
                  fontSize: 13,
                  border: "1px solid rgba(255,255,255,0.10)",
                }}
              >
                {children}
              </table>
            </div>
          ),
          thead: ({ children }) => (
            <thead style={{ background: "rgba(255,255,255,0.04)" }}>{children}</thead>
          ),
          th: ({ children }) => (
            <th
              style={{
                padding: "8px 10px",
                textAlign: "left",
                fontWeight: 600,
                borderBottom: "1px solid rgba(255,255,255,0.10)",
              }}
            >
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td
              style={{
                padding: "8px 10px",
                borderBottom: "1px solid rgba(255,255,255,0.06)",
              }}
            >
              {children}
            </td>
          ),
          hr: () => (
            <hr
              style={{
                border: "none",
                borderTop: "1px solid rgba(255,255,255,0.10)",
                margin: "14px 0",
              }}
            />
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
