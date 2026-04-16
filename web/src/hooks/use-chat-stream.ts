"use client";

import { useCallback, useRef } from "react";
import { useChatStore } from "@/lib/store";
import { fetchConversations } from "@/lib/api";
import type { ChatMessage } from "@/lib/types";

/** Same-origin Next proxy → server uses BACKEND_URL at runtime (Cloud Run). */
const CHAT_URL = "/api/chat";

export function useChatStream() {
  const {
    conversationId,
    messages,
    status,
    searchQuery,
    setConversationId,
    setConversations,
    addMessage,
    updateLastAssistantContent,
    appendSourcesToLastAssistant,
    addToolCallToLastAssistant,
    resolveLastToolCall,
    updateLastAssistantThinking,
    thinkingMode,
    setStatus,
    setSearchQuery,
  } = useChatStore();

  const abortRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(
    async (text: string, images?: string[]) => {
      if (status === "streaming") return;

      const userMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "user",
        content: text,
        images,
        timestamp: new Date().toISOString(),
      };
      addMessage(userMsg);

      const assistantMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: "",
        timestamp: new Date().toISOString(),
      };
      addMessage(assistantMsg);

      setStatus("streaming");
      setSearchQuery(null);

      const controller = new AbortController();
      abortRef.current = controller;
      let accumulated = "";
      let accumulatedThinking = "";

      try {
        const res = await fetch(CHAT_URL, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            conversation_id: conversationId,
            message: text,
            images: images ?? null,
            think: thinkingMode === "off" ? null : thinkingMode,
          }),
          signal: controller.signal,
        });

        if (!res.ok) {
          throw new Error(`API error: ${res.status}`);
        }

        const reader = res.body?.getReader();
        if (!reader) throw new Error("No response body");

        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          let currentEvent = "";
          for (const line of lines) {
            if (line.startsWith("event:")) {
              currentEvent = line.slice(6).trim();
            } else if (line.startsWith("data:")) {
              const raw = line.slice(5).trim();
              if (!raw) continue;

              try {
                const data = JSON.parse(raw);
                switch (currentEvent) {
                  case "thinking":
                    accumulatedThinking += data.content;
                    updateLastAssistantThinking(accumulatedThinking);
                    break;
                  case "text":
                    accumulated += data.content;
                    updateLastAssistantContent(accumulated);
                    break;
                  case "tool_call":
                    addToolCallToLastAssistant({
                      name: data.name,
                      query: data.query,
                      status: "pending",
                    });
                    setStatus("searching");
                    setSearchQuery(data.query);
                    break;
                  case "search_results":
                    resolveLastToolCall();
                    if (data.results?.length) {
                      appendSourcesToLastAssistant(data.results);
                    }
                    setStatus("streaming");
                    setSearchQuery(null);
                    break;
                  case "error":
                    accumulated += `\n\n*Error: ${data.error}*`;
                    updateLastAssistantContent(accumulated);
                    break;
                  case "done":
                    if (data.conversation_id) {
                      setConversationId(data.conversation_id);
                      fetchConversations()
                        .then(setConversations)
                        .catch(() => {});
                    }
                    break;
                }
              } catch {
                // skip malformed JSON
              }
            }
          }
        }

        setStatus("idle");
      } catch (err: unknown) {
        if (err instanceof DOMException && err.name === "AbortError") {
          setStatus("idle");
          return;
        }
        setStatus("error");
        const errMsg = err instanceof Error ? err.message : "Unknown error";
        updateLastAssistantContent(
          accumulated + `\n\n*Error: ${errMsg}*`
        );
      } finally {
        abortRef.current = null;
      }
    },
    [
      conversationId,
      status,
      addMessage,
      updateLastAssistantContent,
      appendSourcesToLastAssistant,
      addToolCallToLastAssistant,
      resolveLastToolCall,
      updateLastAssistantThinking,
      thinkingMode,
      setStatus,
      setSearchQuery,
      setConversationId,
      setConversations,
    ]
  );

  const stopStreaming = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  return {
    messages,
    status,
    searchQuery,
    sendMessage,
    stopStreaming,
  };
}
