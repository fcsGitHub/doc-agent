import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { wikiApi, WikiArticleUpdate } from "@/lib/api/wiki";

export const WIKI_SOURCES_KEY = ["wiki-sources"] as const;
export const WIKI_ARTICLES_KEY = (category?: string) => ["wiki-articles", category] as const;

export function useWikiSources() {
  return useQuery({ queryKey: WIKI_SOURCES_KEY, queryFn: wikiApi.listSources });
}

export function useWikiArticles(category?: string) {
  return useQuery({
    queryKey: WIKI_ARTICLES_KEY(category),
    queryFn: () => wikiApi.listArticles(category),
  });
}

export function useWikiArticle(id: string | null) {
  return useQuery({
    queryKey: ["wiki-article", id],
    queryFn: () => wikiApi.getArticle(id!),
    enabled: !!id,
  });
}

export function useUploadWikiSource() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => wikiApi.uploadSource(file),
    onSuccess: () => qc.invalidateQueries({ queryKey: WIKI_SOURCES_KEY }),
  });
}

export function useUpdateWikiArticle() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: WikiArticleUpdate }) =>
      wikiApi.updateArticle(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: WIKI_ARTICLES_KEY() }),
  });
}

export function useDeleteWikiArticle() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => wikiApi.deleteArticle(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: WIKI_ARTICLES_KEY() }),
  });
}

export function useWikiCompile() {
  const qc = useQueryClient();
  const [progress, setProgress] = useState<Record<string, unknown> | null>(null);
  const [compiling, setCompiling] = useState(false);

  const compile = async () => {
    setCompiling(true);
    setProgress(null);
    try {
      await wikiApi.compile((event) => setProgress(event));
      qc.invalidateQueries({ queryKey: WIKI_SOURCES_KEY });
      qc.invalidateQueries({ queryKey: WIKI_ARTICLES_KEY() });
    } finally {
      setCompiling(false);
    }
  };

  return { compile, compiling, progress };
}

export function useWikiQuery() {
  return useMutation({
    mutationFn: ({ question, category }: { question: string; category?: string }) =>
      wikiApi.query(question, category),
  });
}

export function useWikiLint() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: wikiApi.lint,
    onSuccess: () => qc.invalidateQueries({ queryKey: WIKI_ARTICLES_KEY() }),
  });
}
