import ReactMarkdown from "react-markdown";

interface MarkdownMessageProps {
  children: string;
}

export function MarkdownMessage({ children }: MarkdownMessageProps) {
  return (
    <ReactMarkdown
      components={{
        p: ({ children }) => <p className="my-1 leading-relaxed">{children}</p>,
        ul: ({ children }) => (
          <ul className="my-1 ml-4 space-y-0.5 list-disc">{children}</ul>
        ),
        ol: ({ children }) => (
          <ol className="my-1 ml-4 space-y-0.5 list-decimal">{children}</ol>
        ),
        li: ({ children }) => <li className="leading-relaxed">{children}</li>,
        strong: ({ children }) => (
          <strong className="font-semibold text-charcoal">{children}</strong>
        ),
        em: ({ children }) => <em className="italic">{children}</em>,
        h1: ({ children }) => (
          <h1 className="font-semibold text-base mt-2 mb-1">{children}</h1>
        ),
        h2: ({ children }) => (
          <h2 className="font-semibold text-sm mt-2 mb-1">{children}</h2>
        ),
        h3: ({ children }) => (
          <h3 className="font-medium text-sm mt-1.5 mb-0.5">{children}</h3>
        ),
        code: ({ children }) => (
          <code className="bg-black/5 rounded px-1 py-0.5 text-xs font-mono">
            {children}
          </code>
        ),
        hr: () => <hr className="my-2 border-black/10" />,
      }}
    >
      {children}
    </ReactMarkdown>
  );
}
