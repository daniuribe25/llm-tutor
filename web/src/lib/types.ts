export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  images?: string[];
  timestamp: string;
}

export interface ConversationSummary {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface Conversation {
  id: string;
  title: string;
  messages: ChatMessage[];
  created_at: string;
  updated_at: string;
}

export interface SSETextEvent {
  content: string;
}

export interface SSEToolCallEvent {
  name: string;
  query: string;
}

export interface SSESearchResultsEvent {
  results: Array<{ title: string; url: string; content: string }>;
}

export interface SSEDoneEvent {
  conversation_id: string;
}

export type StreamStatus = "idle" | "streaming" | "searching" | "error";
