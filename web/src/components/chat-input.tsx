"use client";

import { useCallback, useEffect, useRef, useState, type KeyboardEvent } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { FlaskConical, ImagePlus, Send, Square, X, Zap, Brain } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useChatStream } from "@/hooks/use-chat-stream";
import { useChatStore } from "@/lib/store";
import type { ThinkingMode } from "@/lib/types";

const THINKING_OPTIONS: { value: ThinkingMode; label: string; color: string }[] = [
  { value: "off", label: "Fast", color: "text-red-500" },
  { value: "low", label: "Think: Low", color: "text-amber-500" },
  { value: "medium", label: "Think: Medium", color: "text-blue-500" },
  { value: "high", label: "Think: High", color: "text-violet-500" },
];

export function ChatInput() {
  const { status, sendMessage, stopStreaming } = useChatStream();
  const { thinkingMode, setThinkingMode, researchMode, setResearchMode } = useChatStore();
  const isDeepResearch = researchMode === "deep";
  const [input, setInput] = useState("");
  const [images, setImages] = useState<string[]>([]);
  const [modeMenuOpen, setModeMenuOpen] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const modeMenuRef = useRef<HTMLDivElement>(null);

  const isStreaming = status === "streaming" || status === "searching";
  const currentOption = THINKING_OPTIONS.find((o) => o.value === thinkingMode) ?? THINKING_OPTIONS[0];

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (modeMenuRef.current && !modeMenuRef.current.contains(e.target as Node)) {
        setModeMenuOpen(false);
      }
    }
    if (modeMenuOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [modeMenuOpen]);

  const handleSubmit = useCallback(() => {
    const text = input.trim();
    if (!text && images.length === 0) return;
    if (isStreaming) return;

    sendMessage(text, images.length > 0 ? images : undefined);
    setInput("");
    setImages([]);
    textareaRef.current?.focus();
  }, [input, images, isStreaming, sendMessage]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit]
  );

  const handleImageUpload = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = e.target.files;
      if (!files) return;

      Array.from(files).forEach((file) => {
        if (!file.type.startsWith("image/")) return;
        const reader = new FileReader();
        reader.onload = () => {
          const result = reader.result as string;
          const base64 = result.split(",")[1];
          setImages((prev) => [...prev, base64]);
        };
        reader.readAsDataURL(file);
      });

      e.target.value = "";
    },
    []
  );

  const removeImage = useCallback((index: number) => {
    setImages((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const files = e.dataTransfer.files;
    Array.from(files).forEach((file) => {
      if (!file.type.startsWith("image/")) return;
      const reader = new FileReader();
      reader.onload = () => {
        const result = reader.result as string;
        const base64 = result.split(",")[1];
        setImages((prev) => [...prev, base64]);
      };
      reader.readAsDataURL(file);
    });
  }, []);

  return (
    <div className="border-t border-border bg-background p-4">
      <div className="mx-auto max-w-3xl">
        <AnimatePresence>
          {images.length > 0 && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: "auto" }}
              exit={{ opacity: 0, height: 0 }}
              className="mb-3 flex flex-wrap gap-2"
            >
              {images.map((img, i) => (
                <div key={i} className="group relative">
                  <img
                    src={`data:image/png;base64,${img}`}
                    alt={`Upload preview ${i + 1}`}
                    className="h-20 w-20 rounded-lg border border-border object-cover"
                  />
                  <button
                    onClick={() => removeImage(i)}
                    aria-label={`Remove image ${i + 1}`}
                    className="absolute -right-1.5 -top-1.5 rounded-full bg-foreground p-0.5 text-background opacity-0 transition-opacity group-hover:opacity-100"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </div>
              ))}
            </motion.div>
          )}
        </AnimatePresence>

        <div
          className="flex items-center gap-1.5 rounded-2xl border border-border bg-muted/50 px-2 py-1.5 transition-colors focus-within:border-ring focus-within:ring-1 focus-within:ring-ring/20"
          onDrop={handleDrop}
          onDragOver={(e) => e.preventDefault()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            multiple
            className="hidden"
            onChange={handleFileChange}
          />

          <Tooltip>
            <TooltipTrigger
              render={
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="size-9 shrink-0 text-muted-foreground hover:text-foreground"
                  onClick={handleImageUpload}
                  disabled={isStreaming}
                >
                  <ImagePlus className="h-5 w-5" />
                </Button>
              }
            />
            <TooltipContent>Upload images</TooltipContent>
          </Tooltip>

          <div className="relative" ref={modeMenuRef}>
            <Tooltip>
              <TooltipTrigger
                render={
                  <button
                    type="button"
                    onClick={() => setModeMenuOpen((v) => !v)}
                    disabled={isStreaming}
                    aria-expanded={modeMenuOpen}
                    aria-haspopup="menu"
                    className={`inline-flex items-center justify-center size-9 shrink-0 rounded-lg transition-colors hover:bg-muted disabled:opacity-50 ${currentOption.color}`}
                  >
                    {thinkingMode === "off" ? (
                      <Zap className="h-4 w-4" />
                    ) : (
                      <Brain className="h-4 w-4" />
                    )}
                  </button>
                }
              />
              <TooltipContent>{currentOption.label}</TooltipContent>
            </Tooltip>

            <AnimatePresence>
              {modeMenuOpen && (
                <motion.div
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 4 }}
                  transition={{ duration: 0.15 }}
                  className="absolute bottom-full left-0 mb-1 z-50 min-w-[140px] rounded-lg border border-border bg-background p-1 shadow-lg"
                >
                  {THINKING_OPTIONS.map((opt) => (
                    <button
                      key={opt.value}
                      type="button"
                      onClick={() => {
                        setThinkingMode(opt.value);
                        setModeMenuOpen(false);
                      }}
                      className={`flex w-full items-center gap-2 rounded-md px-2.5 py-1.5 text-xs transition-colors ${
                        thinkingMode === opt.value
                          ? "bg-primary/10 font-medium"
                          : "text-muted-foreground hover:bg-muted hover:text-foreground"
                      }`}
                    >
                      {opt.value === "off" ? (
                        <Zap className={`h-3 w-3 ${opt.color}`} />
                      ) : (
                        <Brain className={`h-3 w-3 ${opt.color}`} />
                      )}
                      {opt.label}
                    </button>
                  ))}
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          <Tooltip>
            <TooltipTrigger
              render={
                <button
                  type="button"
                  onClick={() => setResearchMode(isDeepResearch ? "auto" : "deep")}
                  disabled={isStreaming}
                  className={`inline-flex items-center justify-center size-9 shrink-0 rounded-lg transition-colors disabled:opacity-50 ${
                    isDeepResearch
                      ? "bg-violet-100 text-violet-600 dark:bg-violet-950 dark:text-violet-400"
                      : "text-muted-foreground hover:bg-muted hover:text-foreground"
                  }`}
                  aria-label={isDeepResearch ? "Deep Research (on)" : "Deep Research (off)"}
                >
                  <FlaskConical className="h-4 w-4" />
                </button>
              }
            />
            <TooltipContent>
              {isDeepResearch ? "Deep Research: ON — click to disable" : "Deep Research: OFF — click to enable full pipeline"}
            </TooltipContent>
          </Tooltip>

          <Textarea
            ref={textareaRef}
            data-chat-input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask me anything..."
            className="block min-h-10 max-h-[200px] flex-1 resize-none border-0 bg-transparent px-2 py-2 text-sm leading-5 shadow-none focus-visible:border-transparent focus-visible:ring-0 md:min-h-10"
            rows={1}
            disabled={isStreaming}
          />

          {isStreaming ? (
            <Tooltip>
              <TooltipTrigger
                render={
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="size-9 shrink-0 text-red-500 hover:text-red-700"
                    onClick={stopStreaming}
                  >
                    <Square className="h-4 w-4 fill-current" />
                  </Button>
                }
              />
              <TooltipContent>Stop generating</TooltipContent>
            </Tooltip>
          ) : (
            <Tooltip>
              <TooltipTrigger
                render={
                  <Button
                    type="button"
                    size="icon"
                    className="size-9 shrink-0 rounded-xl disabled:opacity-40"
                    variant="default"
                    onClick={handleSubmit}
                    disabled={!input.trim() && images.length === 0}
                  >
                    <Send className="h-4 w-4" />
                  </Button>
                }
              />
              <TooltipContent>Send message</TooltipContent>
            </Tooltip>
          )}
        </div>

        <p className="mt-2 text-center text-xs text-muted-foreground">
          Powered by Ollama &middot; Responses may not always be accurate
        </p>
      </div>
    </div>
  );
}
