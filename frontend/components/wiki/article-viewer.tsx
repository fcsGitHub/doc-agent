"use client";

import { WikiArticle } from "@/lib/api/wiki";
import { useDeleteWikiArticle } from "@/lib/hooks/use-wiki";

interface Props {
  article: WikiArticle;
  onEdit: () => void;
}

export function ArticleViewer({ article, onEdit }: Props) {
  const remove = useDeleteWikiArticle();

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-start justify-between p-4 border-b">
        <div>
          <h1 className="text-xl font-bold text-gray-800">{article.title}</h1>
          <p className="text-xs text-gray-400 mt-1">
            分类：{article.category}
            {article.health_score !== null && (
              <span className={`ml-3 ${article.health_score < 0.5 ? "text-yellow-600" : "text-green-600"}`}>
                健康分：{(article.health_score * 100).toFixed(0)}
              </span>
            )}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={onEdit}
            className="text-sm border border-gray-300 px-3 py-1.5 rounded hover:bg-gray-50"
          >
            编辑
          </button>
          <button
            onClick={() => remove.mutate(article.id)}
            disabled={remove.isPending}
            className="text-sm border border-red-300 text-red-600 px-3 py-1.5 rounded hover:bg-red-50 disabled:opacity-50"
          >
            删除
          </button>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto p-6">
        <pre className="whitespace-pre-wrap text-sm text-gray-800 font-sans">{article.content}</pre>
      </div>
    </div>
  );
}
