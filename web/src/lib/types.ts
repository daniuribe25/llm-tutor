export interface Source {
  title: string;
  url: string;
  content: string;
}

export interface ToolCall {
  name: string;
  query: string;
  status: "pending" | "done";
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  images?: string[];
  sources?: Source[];
  toolCalls?: ToolCall[];
  thinking?: string;
  pipelineStatus?: PipelineStatus;
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

export type ThinkingMode = "off" | "low" | "medium" | "high";

export type ResearchMode = "auto" | "deep";

export type PipelineStep =
  | "routing"
  | "planning"
  | "researching"
  | "synthesizing"
  | "critiquing"
  | "refining";

export interface PipelineStatus {
  step: PipelineStep;
  detail: string;
  progress: number; // 0.0 – 1.0
  completed?: boolean;
}
