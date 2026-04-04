import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";

export interface KnowledgeDocument {
  id: string;
  filename: string;
  file_type: string;
  chunk_count: number;
  created_at: string;
}

export interface KnowledgeStats {
  total_documents: number;
  total_chunks: number;
  last_updated: string | null;
}

export interface SearchResult {
  content: string;
  score: number;
  document_name: string;
}

export function useKnowledgeDocs() {
  return useQuery<KnowledgeDocument[]>({
    queryKey: ["knowledge-docs"],
    queryFn: async () => {
      const res = await apiFetch<{ documents: KnowledgeDocument[] }>("/api/v1/knowledge/documents");
      return res.documents;
    },
  });
}

export function useKnowledgeStats() {
  return useQuery<KnowledgeStats>({
    queryKey: ["knowledge-stats"],
    queryFn: async () => {
      const res = await apiFetch<KnowledgeStats>("/api/v1/knowledge/stats");
      return res;
    },
  });
}

export function useIngestDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (file: File) => {
      const fd = new FormData();
      fd.append("file", file);
      const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
      const res = await fetch(`${API_BASE}/api/v1/knowledge/ingest`, {
        method: "POST",
        body: fd,
      });
      if (!res.ok) {
        throw new Error(`Upload failed: ${await res.text()}`);
      }
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["knowledge-docs"] });
      queryClient.invalidateQueries({ queryKey: ["knowledge-stats"] });
    },
  });
}

export function useDeleteDocument() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await apiFetch(`/api/v1/knowledge/documents/${id}`, {
        method: "DELETE",
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["knowledge-docs"] });
      queryClient.invalidateQueries({ queryKey: ["knowledge-stats"] });
    },
  });
}

export function useSearchKnowledge() {
  return useMutation({
    mutationFn: async ({ query, top_k = 5 }: { query: string; top_k?: number }) => {
      const res = await apiFetch<{ results: SearchResult[] }>("/api/v1/knowledge/search", {
        method: "POST",
        body: JSON.stringify({ query, top_k }),
      });
      return res.results;
    },
  });
}
