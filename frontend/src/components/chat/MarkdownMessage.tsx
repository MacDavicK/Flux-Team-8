import ReactMarkdown from "react-markdown";

interface RagSource {
  title: string;
  url: string | null;
}

interface MarkdownMessageProps {
  children: string;
  ragSources?: RagSource[];
}

/**
 * Replace inline citation markers like [1], [1,3], [1, 3] with markdown links
 * pointing to the corresponding ragSources entry (1-indexed).
 */
function linkifyCitations(text: string, sources: RagSource[]): string {
  return text.replace(/\[(\d+(?:,\s*\d+)*)\]/g, (_, nums: string) => {
    return nums
      .split(",")
      .map((n) => {
        const idx = parseInt(n.trim(), 10) - 1;
        const source = sources[idx];
        if (!source?.url) return `[${n.trim()}]`;
        return `[${n.trim()}](${source.url})`;
      })
      .join("");
  });
}

export function MarkdownMessage({
  children,
  ragSources,
}: MarkdownMessageProps) {
  const content = ragSources?.length
    ? linkifyCitations(children, ragSources)
    : children;

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
        a: ({ href, children }) => (
          <a
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center text-[10px] font-semibold leading-none bg-sage/20 text-sage hover:bg-sage/30 rounded px-1 py-0.5 mx-0.5 transition-colors no-underline"
          >
            {children}
          </a>
        ),
      }}
    >
      {content}
    </ReactMarkdown>
  );
}
