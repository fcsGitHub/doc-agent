"use client";

import { useState } from "react";
import { WikiArticle } from "@/lib/api/wiki";
import { useUpdateWikiArticle } from "@/lib/hooks/use-wiki";

interface Props {
  article: WikiArticle;
  onDone: () => void;
}

export function ArticleEditor({ article, onDone }: Props) {
  const [title, setTitle] = useState(article.title);
  const [category, setCategory] = useState(article.category);
  const [content, setContent] = useState(article.content);
  const [summary, setSummary] = useState(article.summary);
  const update = useUpdateWikiArticle();

  const handleSave = () => {
    update.mutate(
      { id: article.id, data: { title, category, content, summary } },
      { onSuccess: onDone },
    );
  };

  return (
    <div className="flex flex-col h-full p-4 space-y-3">
      <div className="flex gap-2">
        <input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="flex-1 rounded border border-gray-300 px-3 py-2 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-blue-500"
          placeholder="文章标题"
        />
        <select
          value={category}
          onChange={(e) => setCategory(e.target.value)}
          className="rounded border border-gray-300 px-2 py-2 text-sm focus:outline-none"
        >
          <option value="standards">行业规范</option>
          <option value="terms">术语</option>
          <option value="cases">历史案例</option>
          <option value="general">通用</option>
        </select>
      </div>
      <input
        value={summary}
        onChange={(e) => setSummary(e.target.value)}
        className="rounded border border-gray-300 px-3 py-2 text-sm focus:outline-none"
        placeholder="摘要（一句话描述）"
      />
      <textarea
        value={content}
        onChange={(e) => setContent(e.target.value)}
        className="flex-1 rounded border border-gray-300 px-3 py-2 text-sm font-mono focus:outline-none resize-none"
        placeholder="Markdown 内容..."
      />
      <div className="flex gap-2">
        <button
          onClick={handleSave}
          disabled={update.isPending}
          className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700 disabled:opacity-50"
        >
          {update.isPending ? "保存中..." : "保存"}
        </button>
        <button
          onClick={onDone}
          className="border border-gray-300 px-4 py-2 rounded text-sm hover:bg-gray-50"
        >
          取消
        </button>
      </div>
    </div>
  );
}
