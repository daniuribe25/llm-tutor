"use client";

import type { ReactNode } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  BookOpen,
  Check,
  FlaskConical,
  Loader2,
  Pencil,
  Route,
  Search,
  Sparkles,
} from "lucide-react";
import type { PipelineStep, PipelineStatus } from "@/lib/types";

interface ResearchProgressProps {
  pipelineStatus: PipelineStatus;
  isStreaming?: boolean;
}

const STEP_META: Record<
  PipelineStep,
  { label: string; icon: ReactNode; order: number }
> = {
  routing:      { label: "Routing",      icon: <Route className="h-3 w-3" />,        order: 0 },
  planning:     { label: "Planning",     icon: <BookOpen className="h-3 w-3" />,      order: 1 },
  researching:  { label: "Researching",  icon: <Search className="h-3 w-3" />,        order: 2 },
  synthesizing: { label: "Synthesizing", icon: <Pencil className="h-3 w-3" />,        order: 3 },
  critiquing:   { label: "Reviewing",    icon: <FlaskConical className="h-3 w-3" />,  order: 4 },
  refining:     { label: "Refining",     icon: <Sparkles className="h-3 w-3" />,      order: 5 },
};

const PIPELINE_STEPS: PipelineStep[] = [
  "routing",
  "planning",
  "researching",
  "synthesizing",
  "critiquing",
  "refining",
];

export function ResearchProgress({
  pipelineStatus,
  isStreaming,
}: ResearchProgressProps) {
  const { step, detail, progress, completed } = pipelineStatus;
  const meta = STEP_META[step];
  const currentOrder = meta?.order ?? 0;

  const visibleSteps = PIPELINE_STEPS.filter(
    (s) => s !== "routing" && STEP_META[s].order <= currentOrder
  );

  if (completed && visibleSteps.length === 0) return null;

  const hadDeepSteps = visibleSteps.some(
    (s) => s === "critiquing" || s === "refining"
  );
  const completionLabel = hadDeepSteps
    ? "Deep research completed"
    : "Research completed";

  if (completed && !isStreaming) {
    return (
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        className="mb-3 inline-flex items-center gap-1.5 rounded-full border border-border bg-background px-3 py-1 text-xs font-medium text-muted-foreground"
      >
        <Check className="h-3 w-3 text-emerald-500" />
        {completionLabel}
      </motion.div>
    );
  }

  const safeProgress = typeof progress === "number" && !isNaN(progress)
    ? Math.min(progress * 100, 100)
    : 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: -4 }}
      animate={{ opacity: 1, y: 0 }}
      className="mb-3 rounded-lg border border-border bg-background/60 p-3"
    >
      {/* Progress bar */}
      <div className="mb-2.5 h-1 w-full overflow-hidden rounded-full bg-muted">
        <motion.div
          className="h-full rounded-full bg-primary"
          initial={{ width: 0 }}
          animate={{ width: `${safeProgress}%` }}
          transition={{ duration: 0.4, ease: "easeOut" }}
        />
      </div>

      {/* Step pills */}
      <div className="flex flex-wrap items-center gap-1.5">
        {visibleSteps.map((s) => {
          const sMeta = STEP_META[s];
          const isCurrent = s === step;
          const isDone = STEP_META[s].order < currentOrder;

          return (
            <motion.span
              key={s}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[11px] font-medium transition-colors ${
                isCurrent
                  ? "border-primary/30 bg-primary/10 text-primary"
                  : isDone
                  ? "border-emerald-200 bg-emerald-50 text-emerald-700 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-400"
                  : "border-border bg-muted/50 text-muted-foreground"
              }`}
            >
              {isCurrent && isStreaming ? (
                <Loader2 className="h-2.5 w-2.5 animate-spin" />
              ) : isDone ? (
                <Check className="h-2.5 w-2.5" />
              ) : (
                sMeta.icon
              )}
              {sMeta.label}
            </motion.span>
          );
        })}
      </div>

      {/* Current detail text */}
      {detail && (
        <AnimatePresence mode="wait">
          <motion.p
            key={detail}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="mt-2 text-[11px] text-muted-foreground"
          >
            {detail}
          </motion.p>
        </AnimatePresence>
      )}
    </motion.div>
  );
}
