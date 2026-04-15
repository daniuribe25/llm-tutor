"use client";

import { motion, AnimatePresence } from "framer-motion";
import { Globe, Loader2 } from "lucide-react";

interface SearchIndicatorProps {
  query: string | null;
}

export function SearchIndicator({ query }: SearchIndicatorProps) {
  return (
    <AnimatePresence>
      {query && (
        <motion.div
          initial={{ opacity: 0, height: 0 }}
          animate={{ opacity: 1, height: "auto" }}
          exit={{ opacity: 0, height: 0 }}
          className="flex items-center gap-2 px-4 py-2 mx-4 rounded-lg bg-amber-50 border border-amber-200 text-amber-700 text-sm dark:bg-amber-950/30 dark:border-amber-800 dark:text-amber-400"
        >
          <Globe className="h-4 w-4 shrink-0" />
          <span className="truncate">Searching the web: &ldquo;{query}&rdquo;</span>
          <Loader2 className="h-4 w-4 shrink-0 animate-spin ml-auto" />
        </motion.div>
      )}
    </AnimatePresence>
  );
}
