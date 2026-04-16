"use client";

import { useCallback, useEffect, useRef } from "react";
import { AnimatePresence } from "framer-motion";
import { MessageBubble } from "./message-bubble";
import { SearchIndicator } from "./search-indicator";
import { useChatStore } from "@/lib/store";
import { GraduationCap } from "lucide-react";

export function ChatMessages() {
  const { messages, status, searchQuery } = useChatStore();
  const scrollRef = useRef<HTMLDivElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const userScrolledUp = useRef(false);

  const handleScroll = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    userScrolledUp.current = distanceFromBottom > 30;
  }, []);

  const prevMsgCount = useRef(0);
  useEffect(() => {
    const newUserMsg =
      messages.length > prevMsgCount.current &&
      messages.length >= 2 &&
      messages[messages.length - 2]?.role === "user";
    if (newUserMsg) {
      userScrolledUp.current = false;
    }
    prevMsgCount.current = messages.length;

    if (!userScrolledUp.current) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, searchQuery]);

  if (messages.length === 0) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-4 text-center p-8">
        <div className="rounded-full bg-linear-to-br from-violet-500/15 to-fuchsia-500/15 p-6">
          <GraduationCap className="h-12 w-12 text-violet-600 dark:text-violet-400" />
        </div>
        <h2 className="font-heading text-2xl font-semibold tracking-tight text-foreground">
          Welcome to LLM Tutor
        </h2>
        <p className="max-w-md text-muted-foreground">
          Ask me anything and I&apos;ll search the web for the latest information
          to teach you. You can also upload images for me to analyze.
        </p>
        <div className="flex flex-wrap justify-center gap-2 mt-2">
          {[
            "Explain quantum computing",
            "How does photosynthesis work?",
            "Teach me about black holes",
          ].map((suggestion) => (
            <button
              key={suggestion}
              className="rounded-full border border-border px-4 py-2 text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
              onClick={() => {
                const input = document.querySelector<HTMLTextAreaElement>(
                  "[data-chat-input]"
                );
                if (input) {
                  input.value = suggestion;
                  input.focus();
                  input.dispatchEvent(new Event("input", { bubbles: true }));
                }
              }}
            >
              {suggestion}
            </button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div ref={scrollRef} onScroll={handleScroll} className="flex-1 min-h-0 overflow-y-auto">
      <div className="mx-auto max-w-3xl space-y-4 p-4 pb-8">
        <AnimatePresence initial={false}>
          {messages.map((msg, i) => (
            <MessageBubble
              key={msg.id}
              message={msg}
              isStreaming={
                status === "streaming" &&
                msg.role === "assistant" &&
                i === messages.length - 1
              }
            />
          ))}
        </AnimatePresence>
        <SearchIndicator query={searchQuery} />
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
