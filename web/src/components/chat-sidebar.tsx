"use client";

import { useEffect, useCallback, useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Plus, MessageSquare, Trash2, Pencil, PanelLeftClose, Check, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { useChatStore } from "@/lib/store";
import {
  fetchConversations,
  fetchConversation,
  deleteConversation,
  renameConversation,
} from "@/lib/api";

export function ChatSidebar() {
  const {
    conversationId,
    conversations,
    sidebarOpen,
    setConversationId,
    setConversations,
    setMessages,
    setSidebarOpen,
    reset,
  } = useChatStore();

  const loadConversations = useCallback(async () => {
    try {
      const convs = await fetchConversations();
      setConversations(convs);
    } catch {
      // silently fail on initial load
    }
  }, [setConversations]);

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  const handleNewChat = useCallback(() => {
    reset();
    loadConversations();
  }, [reset, loadConversations]);

  const handleSelectConversation = useCallback(
    async (id: string) => {
      try {
        const conv = await fetchConversation(id);
        setConversationId(conv.id);
        setMessages(conv.messages);
      } catch {
        // ignore
      }
    },
    [setConversationId, setMessages]
  );

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const editInputRef = useRef<HTMLInputElement>(null);

  const handleStartRename = useCallback(
    (id: string, currentTitle: string, e: React.MouseEvent) => {
      e.stopPropagation();
      setEditingId(id);
      setEditTitle(currentTitle);
      setTimeout(() => editInputRef.current?.select(), 0);
    },
    []
  );

  const handleConfirmRename = useCallback(async () => {
    if (!editingId) return;
    const trimmed = editTitle.trim();
    if (trimmed) {
      try {
        await renameConversation(editingId, trimmed);
        loadConversations();
      } catch {
        // ignore
      }
    }
    setEditingId(null);
  }, [editingId, editTitle, loadConversations]);

  const handleCancelRename = useCallback(() => {
    setEditingId(null);
  }, []);

  const handleDelete = useCallback(
    async (id: string, e: React.MouseEvent) => {
      e.stopPropagation();
      try {
        await deleteConversation(id);
        if (conversationId === id) reset();
        loadConversations();
      } catch {
        // ignore
      }
    },
    [conversationId, reset, loadConversations]
  );

  return (
    <AnimatePresence>
      {sidebarOpen && (
        <motion.aside
          initial={{ width: 0, opacity: 0 }}
          animate={{ width: 280, opacity: 1 }}
          exit={{ width: 0, opacity: 0 }}
          transition={{ duration: 0.2, ease: "easeInOut" }}
          className="flex h-full flex-col overflow-hidden border-r border-sidebar-border bg-sidebar"
        >
          <div className="flex items-center justify-between p-4">
            <h2 className="font-heading text-sm font-semibold text-sidebar-foreground">
              Conversations
            </h2>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 text-muted-foreground"
              onClick={() => setSidebarOpen(false)}
            >
              <PanelLeftClose className="h-4 w-4" />
            </Button>
          </div>

          <div className="px-3 pb-3">
            <Button
              onClick={handleNewChat}
              className="w-full gap-2 rounded-xl"
              size="sm"
            >
              <Plus className="h-4 w-4" />
              New Chat
            </Button>
          </div>

          <Separator />

          <ScrollArea className="flex-1 px-2 py-2">
            <div className="space-y-1">
              {conversations.map((conv) => (
                <div
                  key={conv.id}
                  role="button"
                  tabIndex={0}
                  onClick={() => editingId !== conv.id && handleSelectConversation(conv.id)}
                  onKeyDown={(e) => {
                    if (editingId === conv.id) return;
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      handleSelectConversation(conv.id);
                    }
                  }}
                  className={`group flex w-full cursor-pointer items-center gap-2 rounded-lg px-3 py-2.5 text-left text-sm transition-colors ${
                    conversationId === conv.id
                      ? "bg-sidebar-accent text-sidebar-accent-foreground"
                      : "text-muted-foreground hover:bg-sidebar-accent/60 hover:text-sidebar-accent-foreground"
                  }`}
                >
                  <MessageSquare className="h-4 w-4 shrink-0" />

                  {editingId === conv.id ? (
                    <form
                      className="flex flex-1 items-center gap-1"
                      onSubmit={(e) => { e.preventDefault(); handleConfirmRename(); }}
                    >
                      <input
                        ref={editInputRef}
                        value={editTitle}
                        onChange={(e) => setEditTitle(e.target.value)}
                        onKeyDown={(e) => { if (e.key === "Escape") handleCancelRename(); }}
                        onClick={(e) => e.stopPropagation()}
                        className="flex-1 rounded border border-border bg-background px-1.5 py-0.5 text-sm text-foreground outline-none focus:ring-1 focus:ring-ring"
                        autoFocus
                      />
                      <button
                        type="submit"
                        onClick={(e) => e.stopPropagation()}
                        className="shrink-0 rounded p-0.5 hover:bg-sidebar-accent"
                      >
                        <Check className="h-3.5 w-3.5 text-emerald-500" />
                      </button>
                      <button
                        type="button"
                        onClick={(e) => { e.stopPropagation(); handleCancelRename(); }}
                        className="shrink-0 rounded p-0.5 hover:bg-sidebar-accent"
                      >
                        <X className="h-3.5 w-3.5 text-muted-foreground" />
                      </button>
                    </form>
                  ) : (
                    <>
                      <span className="flex-1 truncate">{conv.title}</span>
                      <button
                        onClick={(e) => handleStartRename(conv.id, conv.title, e)}
                        className="shrink-0 rounded p-1 opacity-0 transition-opacity hover:bg-sidebar-accent group-hover:opacity-100"
                      >
                        <Pencil className="h-3.5 w-3.5 text-muted-foreground" />
                      </button>
                      <button
                        onClick={(e) => handleDelete(conv.id, e)}
                        className="shrink-0 rounded p-1 opacity-0 transition-opacity hover:bg-sidebar-accent group-hover:opacity-100"
                      >
                        <Trash2 className="h-3.5 w-3.5 text-muted-foreground" />
                      </button>
                    </>
                  )}
                </div>
              ))}

              {conversations.length === 0 && (
                <p className="px-3 py-6 text-center text-xs text-muted-foreground">
                  No conversations yet
                </p>
              )}
            </div>
          </ScrollArea>
        </motion.aside>
      )}
    </AnimatePresence>
  );
}
