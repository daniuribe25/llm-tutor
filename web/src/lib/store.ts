import { create } from "zustand";
import type { ChatMessage, ConversationSummary, Source, StreamStatus } from "./types";

interface ChatState {
  conversationId: string | null;
  conversations: ConversationSummary[];
  messages: ChatMessage[];
  status: StreamStatus;
  searchQuery: string | null;
  sidebarOpen: boolean;

  setConversationId: (id: string | null) => void;
  setConversations: (convs: ConversationSummary[]) => void;
  setMessages: (msgs: ChatMessage[]) => void;
  addMessage: (msg: ChatMessage) => void;
  updateLastAssistantContent: (content: string) => void;
  appendSourcesToLastAssistant: (sources: Source[]) => void;
  setStatus: (status: StreamStatus) => void;
  setSearchQuery: (query: string | null) => void;
  setSidebarOpen: (open: boolean) => void;
  toggleSidebar: () => void;
  reset: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  conversationId: null,
  conversations: [],
  messages: [],
  status: "idle",
  searchQuery: null,
  sidebarOpen: true,

  setConversationId: (id) => set({ conversationId: id }),
  setConversations: (convs) => set({ conversations: convs }),
  setMessages: (msgs) => set({ messages: msgs }),
  addMessage: (msg) =>
    set((s) => ({ messages: [...s.messages, msg] })),
  updateLastAssistantContent: (content) =>
    set((s) => {
      const msgs = [...s.messages];
      const last = msgs[msgs.length - 1];
      if (last?.role === "assistant") {
        msgs[msgs.length - 1] = { ...last, content };
      }
      return { messages: msgs };
    }),
  appendSourcesToLastAssistant: (sources) =>
    set((s) => {
      const msgs = [...s.messages];
      const last = msgs[msgs.length - 1];
      if (last?.role === "assistant") {
        msgs[msgs.length - 1] = {
          ...last,
          sources: [...(last.sources ?? []), ...sources],
        };
      }
      return { messages: msgs };
    }),
  setStatus: (status) => set({ status }),
  setSearchQuery: (query) => set({ searchQuery: query }),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  reset: () =>
    set({
      conversationId: null,
      messages: [],
      status: "idle",
      searchQuery: null,
    }),
}));
