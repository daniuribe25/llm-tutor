import { create } from "zustand";
import type { ChatMessage, ConversationSummary, Source, StreamStatus, ThinkingMode, ToolCall } from "./types";

interface ChatState {
  conversationId: string | null;
  conversations: ConversationSummary[];
  messages: ChatMessage[];
  status: StreamStatus;
  searchQuery: string | null;
  thinkingMode: ThinkingMode;
  sidebarOpen: boolean;

  setConversationId: (id: string | null) => void;
  setConversations: (convs: ConversationSummary[]) => void;
  setMessages: (msgs: ChatMessage[]) => void;
  addMessage: (msg: ChatMessage) => void;
  updateLastAssistantContent: (content: string) => void;
  appendSourcesToLastAssistant: (sources: Source[]) => void;
  addToolCallToLastAssistant: (tc: ToolCall) => void;
  resolveLastToolCall: () => void;
  updateLastAssistantThinking: (thinking: string) => void;
  setStatus: (status: StreamStatus) => void;
  setThinkingMode: (mode: ThinkingMode) => void;
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
  thinkingMode: "off",
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
  addToolCallToLastAssistant: (tc) =>
    set((s) => {
      const msgs = [...s.messages];
      const last = msgs[msgs.length - 1];
      if (last?.role === "assistant") {
        msgs[msgs.length - 1] = {
          ...last,
          toolCalls: [...(last.toolCalls ?? []), tc],
        };
      }
      return { messages: msgs };
    }),
  resolveLastToolCall: () =>
    set((s) => {
      const msgs = [...s.messages];
      const last = msgs[msgs.length - 1];
      if (last?.role === "assistant" && last.toolCalls?.length) {
        const tcs = [...last.toolCalls];
        for (let i = tcs.length - 1; i >= 0; i--) {
          if (tcs[i].status === "pending") {
            tcs[i] = { ...tcs[i], status: "done" };
            break;
          }
        }
        msgs[msgs.length - 1] = { ...last, toolCalls: tcs };
      }
      return { messages: msgs };
    }),
  updateLastAssistantThinking: (thinking) =>
    set((s) => {
      const msgs = [...s.messages];
      const last = msgs[msgs.length - 1];
      if (last?.role === "assistant") {
        msgs[msgs.length - 1] = { ...last, thinking };
      }
      return { messages: msgs };
    }),
  setStatus: (status) => set({ status }),
  setThinkingMode: (mode) => set({ thinkingMode: mode }),
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
