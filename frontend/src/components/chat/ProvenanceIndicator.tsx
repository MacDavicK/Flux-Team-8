import { ArrowUpRight } from "lucide-react";
import { useState } from "react";

interface ProvenanceIndicatorProps {
  ragUsed: boolean;
  ragSources: { title: string; url: string | null }[];
}

export function ProvenanceIndicator({
  ragUsed,
  ragSources,
}: ProvenanceIndicatorProps) {
  const [expanded, setExpanded] = useState(false);
  const showSources = ragUsed && ragSources.length > 0;

  if (showSources) {
    return (
      <div className="mt-1 px-1">
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          aria-expanded={expanded}
          className="flex items-center text-xs text-muted-foreground hover:text-muted-foreground/80 transition-colors"
        >
          Sources cited
          <ArrowUpRight className="w-3 h-3 inline-block ml-0.5" />
        </button>
        {expanded && (
          <ul className="mt-1 space-y-0.5">
            {ragSources.map((source, index) => (
              <li
                key={`${index}-${source.title}`}
                className="text-xs text-muted-foreground"
              >
                {source.url ? (
                  <a
                    href={source.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="hover:underline"
                  >
                    {source.title}
                  </a>
                ) : (
                  source.title
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    );
  }

  return (
    <p className="mt-1 px-1 text-xs text-muted-foreground">
      AI-generated plan · always verify with a professional
    </p>
  );
}
