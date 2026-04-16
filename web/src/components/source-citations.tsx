"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, ExternalLink, Globe } from "lucide-react";
import type { Source } from "@/lib/types";

interface SourceCitationsProps {
  sources: Source[];
}

export function SourceCitations({ sources }: SourceCitationsProps) {
  const [open, setOpen] = useState(false);

  if (!sources.length) return null;

  const unique = sources.filter(
    (s, i, arr) => arr.findIndex((x) => x.url === s.url) === i,
  );

  return (
    <div className="mt-2">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="inline-flex items-center gap-1.5 rounded-full border border-border bg-background px-3 py-1 text-xs font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
      >
        <Globe className="h-3 w-3" />
        {unique.length} {unique.length === 1 ? "source" : "sources"}
        <ChevronDown
          className={`h-3 w-3 transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>

      <AnimatePresence>
        {open && (
          <motion.ul
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="mt-2 flex flex-col gap-2 overflow-hidden"
          >
            {unique.map((src, i) => (
              <li
                key={src.url || i}
                className="rounded-lg border border-border bg-background p-3"
              >
                <a
                  href={src.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="group flex items-start gap-2"
                >
                  <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded bg-primary/10 text-[10px] font-bold text-primary">
                    {i + 1}
                  </span>
                  <div className="min-w-0 flex-1">
                    <span className="line-clamp-1 text-sm font-medium text-foreground group-hover:underline">
                      {src.title || src.url}
                    </span>
                    {src.content && (
                      <p className="mt-0.5 line-clamp-2 text-xs text-muted-foreground">
                        {src.content.slice(0, 150)}
                      </p>
                    )}
                    <span className="mt-1 inline-flex items-center gap-1 text-[10px] text-muted-foreground/70">
                      <ExternalLink className="h-2.5 w-2.5" />
                      {(() => {
                        try {
                          return new URL(src.url).hostname.replace(/^www\./, "");
                        } catch {
                          return src.url || "";
                        }
                      })()}
                    </span>
                  </div>
                </a>
              </li>
            ))}
          </motion.ul>
        )}
      </AnimatePresence>
    </div>
  );
}
