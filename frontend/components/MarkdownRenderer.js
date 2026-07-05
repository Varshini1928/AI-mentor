"use client";

import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";

export default function MarkdownRenderer({ content }) {
  return (
    <div className="prose prose-invert prose-sm sm:prose-base max-w-none">
      <ReactMarkdown
        components={{
          code({ inline, className, children, ...props }) {
            const match = /language-(\w+)/.exec(className || "");
            if (!inline && match) {
              return (
                <SyntaxHighlighter
                  style={oneDark}
                  language={match[1]}
                  PreTag="div"
                  customStyle={{ borderRadius: "0.5rem", fontSize: "0.85rem" }}
                  {...props}
                >
                  {String(children).replace(/\n$/, "")}
                </SyntaxHighlighter>
              );
            }
            return (
              <code
                className="rounded bg-slate-800 px-1.5 py-0.5 text-pink-300"
                {...props}
              >
                {children}
              </code>
            );
          },
          h2({ children }) {
            return (
              <h2 className="mt-4 mb-2 text-lg font-semibold text-indigo-300">
                {children}
              </h2>
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
