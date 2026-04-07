"use client";

import { useWikiArticles } from "@/lib/hooks/use-wiki";
import { WikiArticle } from "@/lib/api/wiki";

interface Props {
  selectedId: string | null;
  onSelect: (article: WikiArticle) => void;
}

const CATEGORY_LABELS: Record<string, string> = {
  standards: "行业规范",
  terms: "术语",
  cases: "历史案例",
  general: "通用",
};

export function ArticleTree({ selectedId, onSelect }: Props) {
  const { data: articles, isLoading } = useWikiArticles();

  if (isLoading) return <div className="p-4 text-sm text-gray-400">加载中...</div>;
  if (!articles?.length) return <div className="p-4 text-sm text-gray-400">暂无文章</div>;

  const grouped = articles.reduce<Record<string, WikiArticle[]>>((acc, a) => {
    const cat = a.category || "general";
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(a);
    return acc;
  }, {});

  return (
    <nav className="space-y-4 p-3">
      {Object.entries(grouped).map(([cat, items]) => (
        <div key={cat}>
          <p className="text-xs font-semibold text-gray-500 uppercase px-2 mb-1">
            {CATEGORY_LABELS[cat] ?? cat}
          </p>
          <ul className="space-y-0.5">
            {items.map((a) => (
              <li key={a.id}>
                <button
                  onClick={() => onSelect(a)}
                  className={`w-full text-left text-sm px-2 py-1.5 rounded transition-colors truncate ${
                    selectedId === a.id
                      ? "bg-blue-100 text-blue-700"
                      : "text-gray-700 hover:bg-gray-100"
                  }`}
                  title={a.title}
                >
                  {a.health_score !== null && a.health_score < 0.5 && (
                    <span className="mr-1 text-yellow-500">⚠</span>
                  )}
                  {a.title}
                </button>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </nav>
  );
}
