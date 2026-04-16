"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, Globe, Check, Loader2, Brain } from "lucide-react";
import type { ToolCall } from "@/lib/types";

interface ReasoningStepsProps {
  toolCalls: ToolCall[];
  isStreaming?: boolean;
}

const TOOL_LABELS: Record<string, string> = {
  search_web: "Searched the web",
};

export function ReasoningSteps({ toolCalls, isStreaming }: ReasoningStepsProps) {
  const [open, setOpen] = useState(true);

  useEffect(() => {
    if (!isStreaming) return;
    setOpen(true);
  }, [isStreaming, toolCalls.length]);

  if (!toolCalls.length) return null;

  const hasPending = toolCalls.some((tc) => tc.status === "pending");

  return (
    <div className="mb-3">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="inline-flex items-center gap-1.5 rounded-full border border-border bg-background px-3 py-1 text-xs font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
      >
        {hasPending ? (
          <Loader2 className="h-3 w-3 animate-spin" />
        ) : (
          <Brain className="h-3 w-3" />
        )}
        Reasoning ({toolCalls.length} {toolCalls.length === 1 ? "step" : "steps"})
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
            <div className="mt-2 border-l-2 border-border pl-3 space-y-2">
              {toolCalls.map((tc, i) => (
                <div
                  key={`${tc.name}-${tc.query}-${i}`}
                  className="flex items-start gap-2 text-xs"
                >
                  <span className="mt-0.5 shrink-0">
                    {tc.status === "pending" ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin text-amber-500" />
                    ) : (
                      <Check className="h-3.5 w-3.5 text-emerald-500" />
                    )}
                  </span>
                  <span className="flex items-center gap-1.5 text-muted-foreground">
                    <Globe className="h-3 w-3 shrink-0" />
                    <span>
                      {TOOL_LABELS[tc.name] ?? tc.name}:{" "}
                      <span className="italic text-foreground/80">
                        &ldquo;{tc.query}&rdquo;
                      </span>
                    </span>
                  </span>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
