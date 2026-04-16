import type { Conversation, ConversationSummary } from "./types";

/** Same-origin Next proxy → server uses BACKEND_URL at runtime (Cloud Run). */
const API = "/api/conversations";

export async function fetchConversations(): Promise<ConversationSummary[]> {
  const res = await fetch(API);
  if (!res.ok) throw new Error("Failed to fetch conversations");
  return res.json();
}

export async function fetchConversation(id: string): Promise<Conversation> {
  const res = await fetch(`${API}/${id}`);
  if (!res.ok) throw new Error("Failed to fetch conversation");
  return res.json();
}

export async function createConversation(): Promise<Conversation> {
  const res = await fetch(API, { method: "POST" });
  if (!res.ok) throw new Error("Failed to create conversation");
  return res.json();
}

export async function renameConversation(id: string, title: string): Promise<void> {
  const res = await fetch(`${API}/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
  if (!res.ok) throw new Error("Failed to rename conversation");
}

export async function deleteConversation(id: string): Promise<void> {
  const res = await fetch(`${API}/${id}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to delete conversation");
}
