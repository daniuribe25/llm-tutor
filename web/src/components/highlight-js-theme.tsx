"use client";

import { useTheme } from "next-themes";
import { useEffect } from "react";

const LINK_ID = "hljs-theme-stylesheet";

/**
 * Swap highlight.js base stylesheet when the app theme changes (global import is theme-agnostic).
 */
export function HighlightJsTheme() {
  const { resolvedTheme } = useTheme();

  useEffect(() => {
    const mode = resolvedTheme === "light" ? "light" : "dark";
    let el = document.getElementById(LINK_ID) as HTMLLinkElement | null;
    if (!el) {
      el = document.createElement("link");
      el.id = LINK_ID;
      el.rel = "stylesheet";
      document.head.appendChild(el);
    }
    el.href =
      mode === "light" ? "/hljs/github.css" : "/hljs/github-dark.css";
  }, [resolvedTheme]);

  return null;
}
