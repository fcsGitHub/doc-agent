import { apiFetch, API_BASE } from "@/lib/api";
import { parseSSEStream } from "@/lib/api/sse-stream";

export interface WikiSource {
  id: string;
  filename: string;
  compiled: boolean;
  uploaded_at: string;
}

export interface WikiArticle {
  id: string;
  title: string;
  category: string;
  content: string;
  summary: string;
  backlinks: string[];
  source_doc_ids: string[];
  health_score: number | null;
  created_at: string;
  updated_at: string;
}

export interface WikiArticleUpdate {
  title?: string;
  category?: string;
  content?: string;
  summary?: string;
}

export interface WikiQueryResponse {
  answer: string;
  source_article_ids: string[];
}

export interface WikiLintReport {
  total_articles: number;
  issues: { type: string; article_id: string | null; article_title: string; description: string; suggestion: string }[];
  updated_scores: Record<string, number>;
}

export const wikiApi = {
  listSources: () => apiFetch<WikiSource[]>("/api/v1/wiki/sources"),

  uploadSource: async (file: File): Promise<WikiSource> => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${API_BASE}/api/v1/wiki/sources`, { method: "POST", body: form });
    if (!res.ok) throw new Error(`Upload failed: ${res.status}`);
    return res.json();
  },

  listArticles: (category?: string) => {
    const qs = category ? `?category=${encodeURIComponent(category)}` : "";
    return apiFetch<WikiArticle[]>(`/api/v1/wiki/articles${qs}`);
  },

  getArticle: (id: string) => apiFetch<WikiArticle>(`/api/v1/wiki/articles/${id}`),

  updateArticle: (id: string, data: WikiArticleUpdate) =>
    apiFetch<WikiArticle>(`/api/v1/wiki/articles/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  deleteArticle: (id: string) =>
    fetch(`${API_BASE}/api/v1/wiki/articles/${id}`, { method: "DELETE" }),

  compile: async (onEvent: (event: Record<string, unknown>) => void): Promise<void> => {
    const res = await fetch(`${API_BASE}/api/v1/wiki/compile`, { method: "POST" });
    if (!res.ok) throw new Error(`Compile failed: ${res.status}`);
    await parseSSEStream(res, (data) => onEvent(data as Record<string, unknown>));
  },

  query: (question: string, category?: string) =>
    apiFetch<WikiQueryResponse>("/api/v1/wiki/query", {
      method: "POST",
      body: JSON.stringify({ question, category: category ?? null }),
    }),

  lint: () => apiFetch<WikiLintReport>("/api/v1/wiki/lint", { method: "POST" }),
};
