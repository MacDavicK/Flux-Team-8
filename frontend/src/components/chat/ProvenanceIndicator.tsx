import { BookOpen, ChevronDown, ExternalLink } from "lucide-react";
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
      <div className="mt-2">
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          aria-expanded={expanded}
          className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-sage/10 border border-sage/20 text-sage text-[11px] font-medium transition-all hover:bg-sage/20 active:scale-95"
        >
          <BookOpen className="w-3 h-3" />
          {ragSources.length} source{ragSources.length !== 1 ? "s" : ""}
          <ChevronDown
            className={`w-3 h-3 transition-transform duration-200 ${expanded ? "rotate-180" : ""}`}
          />
        </button>
        {expanded && (
          <ul
            className="mt-2 rounded-2xl overflow-hidden border border-white/40"
            style={{
              background: "rgba(255,255,255,0.35)",
              backdropFilter: "blur(12px)",
              boxShadow: "0 4px 16px rgba(92,124,102,0.1)",
            }}
          >
            {ragSources.map((source, index) => (
              <li
                key={`${index}-${source.title}`}
                className="flex items-start gap-2 px-3 py-2 border-b border-white/30 last:border-b-0"
              >
                <span className="mt-0.5 flex-shrink-0 w-4 h-4 rounded-full bg-sage/15 text-sage text-[9px] font-semibold flex items-center justify-center">
                  {index + 1}
                </span>
                {source.url ? (
                  <a
                    href={source.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[11px] text-charcoal/70 leading-snug flex-1 flex items-start justify-between gap-1 group"
                  >
                    <span className="group-hover:text-sage transition-colors">
                      {source.title}
                    </span>
                    <ExternalLink className="w-2.5 h-2.5 flex-shrink-0 mt-0.5 text-sage/50 group-hover:text-sage transition-colors" />
                  </a>
                ) : (
                  <span className="text-[11px] text-charcoal/70 leading-snug flex-1">
                    {source.title}
                  </span>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    );
  }

  return (
    <p className="mt-2 text-[11px] text-charcoal/40 italic">
      AI-generated · verify with a professional
    </p>
  );
}
