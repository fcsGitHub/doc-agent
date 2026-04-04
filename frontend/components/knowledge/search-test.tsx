"use client";

import { useState, FormEvent } from "react";
import { useSearchKnowledge } from "@/lib/hooks/use-knowledge";

export function SearchTest() {
  const [query, setQuery] = useState("");
  const { mutate, data: results, isPending } = useSearchKnowledge();

  const handleSearch = (e: FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    mutate({ query: query.trim(), top_k: 5 });
  };

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
      <h2 className="mb-4 text-lg font-semibold text-gray-900">知识库搜索测试</h2>
      
      <form onSubmit={handleSearch} className="mb-6 flex gap-2">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="输入搜索关键词..."
          className="flex-1 rounded-md border border-gray-300 px-4 py-2 text-sm outline-none ring-blue-500 focus:ring-2"
        />
        <button
          type="submit"
          disabled={isPending || !query.trim()}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isPending ? "搜索中..." : "搜索"}
        </button>
      </form>

      {results && results.length > 0 && (
        <div className="space-y-4">
          <h3 className="text-sm font-medium text-gray-700">搜索结果 (Top 5)</h3>
          <div className="flex flex-col gap-4">
            {results.map((res, i) => (
              <div key={i} className="rounded-md bg-gray-50 p-4 text-sm">
                <div className="mb-2 flex items-center justify-between">
                  <span className="font-medium text-blue-600">{res.document_name}</span>
                  <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs text-blue-800">
                    相关度: {res.score.toFixed(3)}
                  </span>
                </div>
                <p className="whitespace-pre-wrap text-gray-700">{res.content}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {results && results.length === 0 && (
        <div className="py-8 text-center text-sm text-gray-500">
          未找到相关内容
        </div>
      )}
    </div>
  );
}
