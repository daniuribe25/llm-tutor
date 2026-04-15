"use client";

import { PanelLeft } from "lucide-react";
import { ChatSidebar } from "@/components/chat-sidebar";
import { ChatMessages } from "@/components/chat-messages";
import { ChatInput } from "@/components/chat-input";
import { ThemeToggle } from "@/components/theme-toggle";
import { Button } from "@/components/ui/button";
import { useChatStore } from "@/lib/store";

export default function Home() {
  const { sidebarOpen, setSidebarOpen } = useChatStore();

  return (
    <div className="flex h-full overflow-hidden bg-background">
      <ChatSidebar />

      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex items-center gap-3 border-b border-border px-4 py-3">
          {!sidebarOpen && (
            <Button
              variant="ghost"
              size="icon"
              className="h-8 w-8 text-muted-foreground"
              onClick={() => setSidebarOpen(true)}
            >
              <PanelLeft className="h-4 w-4" />
            </Button>
          )}
          <div className="flex min-w-0 flex-1 items-center gap-2">
            <div className="h-2.5 w-2.5 shrink-0 rounded-full bg-emerald-500 animate-pulse" />
            <h1 className="font-heading truncate text-sm font-medium text-foreground">
              LLM Tutor
            </h1>
          </div>
          <ThemeToggle />
        </header>

        <ChatMessages />
        <ChatInput />
      </div>
    </div>
  );
}
