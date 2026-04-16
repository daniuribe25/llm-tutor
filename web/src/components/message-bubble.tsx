"use client";

import { motion } from "framer-motion";
import { Bot, User } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { MarkdownRenderer } from "./markdown-renderer";
import { ThinkingBlock } from "./thinking-block";
import { ReasoningSteps } from "./reasoning-steps";
import { SourceCitations } from "./source-citations";
import type { ChatMessage } from "@/lib/types";

interface MessageBubbleProps {
  message: ChatMessage;
  isStreaming?: boolean;
}

export function MessageBubble({ message, isStreaming }: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: "easeOut" }}
      className={`flex gap-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}
    >
      <Avatar className="h-8 w-8 shrink-0 mt-1">
        <AvatarFallback
          className={
            isUser
              ? "bg-blue-600 text-white"
              : "bg-linear-to-br from-violet-500 to-fuchsia-500 text-white"
          }
        >
          {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
        </AvatarFallback>
      </Avatar>

      <div
        className={`flex flex-col max-w-[75%] ${isUser ? "items-end" : "items-start"}`}
      >
        {message.images && message.images.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-2">
            {message.images.map((img, i) => (
              <img
                key={i}
                src={
                  img.startsWith("data:") ? img : `data:image/png;base64,${img}`
                }
                alt={`Uploaded image ${i + 1}`}
                className="max-h-48 rounded-lg border border-border object-cover"
              />
            ))}
          </div>
        )}

        <div
          className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
            isUser
              ? "rounded-br-md bg-primary text-primary-foreground"
              : "rounded-bl-md bg-muted text-foreground"
          }`}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : (
            <div className="prose-sm max-w-none">
              {message.thinking && (
                <ThinkingBlock
                  thinking={message.thinking}
                  isStreaming={isStreaming}
                />
              )}
              {message.toolCalls && message.toolCalls.length > 0 && (
                <ReasoningSteps
                  toolCalls={message.toolCalls}
                  isStreaming={isStreaming}
                />
              )}
              {message.content ? (
                <MarkdownRenderer content={message.content} />
              ) : isStreaming ? (
                <StreamingDots />
              ) : null}
              {message.sources && message.sources.length > 0 && (
                <SourceCitations sources={message.sources} />
              )}
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}

function StreamingDots() {
  return (
    <div className="flex items-center gap-1 py-1">
      {[0, 1, 2].map((i) => (
        <motion.span
          key={i}
          className="h-2 w-2 rounded-full bg-muted-foreground/50"
          animate={{ opacity: [0.3, 1, 0.3] }}
          transition={{
            duration: 1.2,
            repeat: Infinity,
            delay: i * 0.2,
          }}
        />
      ))}
    </div>
  );
}
