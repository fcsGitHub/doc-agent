"use client";

import { useState, useRef } from "react";
import { ArticleTree } from "@/components/wiki/article-tree";
import { ArticleViewer } from "@/components/wiki/article-viewer";
import { ArticleEditor } from "@/components/wiki/article-editor";
import { LintReport } from "@/components/wiki/lint-report";
import {
  useWikiSources,
  useUploadWikiSource,
  useWikiCompile,
  useWikiQuery,
  useWikiLint,
} from "@/lib/hooks/use-wiki";
import { WikiArticle } from "@/lib/api/wiki";

type View = "articles" | "sources" | "query" | "lint";

const VIEW_LABELS: Record<View, string> = {
  articles: "文章",
  sources: "源文件",
  query: "问答",
  lint: "检查",
};

export default function WikiPage() {
  const [view, setView] = useState<View>("articles");
  const [selectedArticle, setSelectedArticle] = useState<WikiArticle | null>(null);
  const [editing, setEditing] = useState(false);
  const [question, setQuestion] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  const { data: sources } = useWikiSources();
  const uploadSource = useUploadWikiSource();
  const { compile, compiling, progress } = useWikiCompile();
  const queryWiki = useWikiQuery();
  const lintWiki = useWikiLint();

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) uploadSource.mutate(file);
  };

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-gray-800">LLM Wiki 知识库</h1>
      <div className="flex h-[calc(100vh-200px)] bg-white rounded-lg border border-gray-200 overflow-hidden">
        {/* Left panel */}
        <div className="w-64 border-r border-gray-200 overflow-y-auto shrink-0 flex flex-col">
          <div className="flex border-b border-gray-200 text-xs shrink-0">
            {(["articles", "sources", "query", "lint"] as View[]).map((v) => (
              <button
                key={v}
                onClick={() => setView(v)}
                className={`flex-1 py-2 ${
                  view === v ? "bg-blue-50 text-blue-700 font-medium" : "text-gray-500 hover:bg-gray-50"
                }`}
              >
                {VIEW_LABELS[v]}
              </button>
            ))}
          </div>

          <div className="flex-1 overflow-y-auto">
            {view === "articles" && (
              <ArticleTree
                selectedId={selectedArticle?.id ?? null}
                onSelect={(a) => { setSelectedArticle(a); setEditing(false); }}
              />
            )}

            {view === "sources" && (
              <div className="p-3 space-y-2">
                <input
                  ref={fileRef}
                  type="file"
                  accept=".md,.txt,.docx,.pdf"
                  className="hidden"
                  onChange={handleFileUpload}
                />
                <button
                  onClick={() => fileRef.current?.click()}
                  className="w-full text-sm bg-blue-600 text-white py-2 rounded hover:bg-blue-700"
                >
                  上传源文件
                </button>
                <button
                  onClick={compile}
                  disabled={compiling}
                  className="w-full text-sm border border-blue-600 text-blue-600 py-2 rounded hover:bg-blue-50 disabled:opacity-50"
                >
                  {compiling ? "编译中..." : "一键编译"}
                </button>
                {progress && (
                  <p className="text-xs text-gray-500 break-words">{JSON.stringify(progress)}</p>
                )}
                <ul className="space-y-1 mt-2">
                  {sources?.map((s) => (
                    <li key={s.id} className="text-xs flex items-center gap-1 text-gray-600">
                      <span>{s.compiled ? "✓" : "○"}</span>
                      <span className="truncate">{s.filename}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {view === "query" && (
              <div className="p-3 space-y-2">
                <textarea
                  value={question}
                  onChange={(e) => setQuestion(e.target.value)}
                  placeholder="输入问题..."
                  rows={4}
                  className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm resize-none focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
                <button
                  onClick={() => queryWiki.mutate({ question })}
                  disabled={queryWiki.isPending || !question.trim()}
                  className="w-full text-sm bg-blue-600 text-white py-2 rounded hover:bg-blue-700 disabled:opacity-50"
                >
                  {queryWiki.isPending ? "查询中..." : "提问"}
                </button>
              </div>
            )}

            {view === "lint" && (
              <div className="p-3 text-xs text-gray-400">点击右侧运行检查</div>
            )}
          </div>
        </div>

        {/* Right panel */}
        <div className="flex-1 overflow-y-auto">
          {view === "query" && queryWiki.data && (
            <div className="p-6">
              <h2 className="text-lg font-semibold mb-3">回答</h2>
              <div className="whitespace-pre-wrap text-sm text-gray-800">{queryWiki.data.answer}</div>
              {queryWiki.data.source_article_ids.length > 0 && (
                <p className="text-xs text-gray-400 mt-4">
                  来源文章 ID：{queryWiki.data.source_article_ids.join(", ")}
                </p>
              )}
            </div>
          )}

          {view === "lint" && (
            <div className="p-6">
              <LintReport
                report={lintWiki.data ?? null}
                onRun={() => lintWiki.mutate()}
                isRunning={lintWiki.isPending}
              />
            </div>
          )}

          {view === "articles" && selectedArticle && !editing && (
            <ArticleViewer article={selectedArticle} onEdit={() => setEditing(true)} />
          )}

          {view === "articles" && selectedArticle && editing && (
            <ArticleEditor article={selectedArticle} onDone={() => setEditing(false)} />
          )}

          {view === "articles" && !selectedArticle && (
            <div className="flex items-center justify-center h-full text-gray-400 text-sm">
              从左侧选择文章查看
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
