import { apiFetch, API_BASE } from "@/lib/api";

export interface ChatSession {
  id: string;
  task_id: string;
  scope: "task" | "section";
  section_id: string | null;
  review_criteria: { label: string; description: string }[];
  created_at: string;
}

export interface ChatMessage {
  id: string;
  session_id: string;
  role: "user" | "assistant";
  content: string;
  action: { type: string; section_id: string; instruction: string; status: string } | null;
  created_at: string;
}

export const chatApi = {
  createSession: (taskId: string, scope: "task" | "section" = "task", sectionId?: string) =>
    apiFetch<ChatSession>(`/api/v1/tasks/${taskId}/chat/sessions`, {
      method: "POST",
      body: JSON.stringify({ scope, section_id: sectionId ?? null }),
    }),

  listSessions: (taskId: string) =>
    apiFetch<ChatSession[]>(`/api/v1/tasks/${taskId}/chat/sessions`),

  listMessages: (sessionId: string) =>
    apiFetch<ChatMessage[]>(`/api/v1/chat/sessions/${sessionId}/messages`),

  sendMessage: async (
    sessionId: string,
    content: string,
    onChunk: (data: { reply: string; intent: string; action: ChatMessage["action"] } | { error: string }) => void,
    onDone: () => void,
  ) => {
    const res = await fetch(`${API_BASE}/api/v1/chat/sessions/${sessionId}/messages`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
    });
    if (!res.ok) throw new Error(`Chat error ${res.status}`);
    const reader = res.body!.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop() ?? "";
      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const payload = line.slice(6).trim();
          if (payload === "[DONE]") { onDone(); return; }
          try { onChunk(JSON.parse(payload)); } catch { /* ignore malformed */ }
        }
      }
    }
    onDone();
  },
};
