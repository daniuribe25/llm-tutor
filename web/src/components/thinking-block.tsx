"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, Lightbulb, Loader2 } from "lucide-react";

interface ThinkingBlockProps {
  thinking: string;
  isStreaming?: boolean;
}

export function ThinkingBlock({ thinking, isStreaming }: ThinkingBlockProps) {
  const [open, setOpen] = useState(true);

  useEffect(() => {
    if (!isStreaming) setOpen(false);
  }, [isStreaming]);

  if (!thinking) return null;

  return (
    <div className="mb-3">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="inline-flex items-center gap-1.5 rounded-full border border-border bg-background px-3 py-1 text-xs font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
      >
        {isStreaming ? (
          <Loader2 className="h-3 w-3 animate-spin" />
        ) : (
          <Lightbulb className="h-3 w-3" />
        )}
        {isStreaming ? "Thinking..." : "View thinking"}
        <ChevronDown
          className={`h-3 w-3 transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="mt-2 rounded-lg border border-border bg-background/60 p-3 text-xs leading-relaxed text-muted-foreground whitespace-pre-wrap max-h-64 overflow-y-auto">
              {thinking}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
