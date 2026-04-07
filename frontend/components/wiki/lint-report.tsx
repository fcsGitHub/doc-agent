"use client";

import { WikiLintReport as LintData } from "@/lib/api/wiki";

interface Props {
  report: LintData | null;
  onRun: () => void;
  isRunning: boolean;
}

const ISSUE_TYPE_LABEL: Record<string, string> = {
  contradiction: "矛盾",
  orphan: "孤立文章",
  missing_reference: "引用缺失",
  low_quality: "质量偏低",
};

export function LintReport({ report, onRun, isRunning }: Props) {
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <button
          onClick={onRun}
          disabled={isRunning}
          className="bg-yellow-500 text-white px-4 py-2 rounded text-sm hover:bg-yellow-600 disabled:opacity-50"
        >
          {isRunning ? "检查中..." : "运行健康检查"}
        </button>
        {report && (
          <span className="text-sm text-gray-500">
            共 {report.total_articles} 篇，发现 {report.issues.length} 个问题
          </span>
        )}
      </div>

      {report && report.issues.length > 0 && (
        <div className="space-y-2">
          {report.issues.map((issue, i) => (
            <div key={i} className="rounded border border-yellow-200 bg-yellow-50 p-3 text-sm">
              <div className="flex items-center gap-2 mb-1">
                <span className="font-medium text-yellow-800">
                  {ISSUE_TYPE_LABEL[issue.type] ?? issue.type}
                </span>
                {issue.article_title && (
                  <span className="text-gray-600">— {issue.article_title}</span>
                )}
              </div>
              <p className="text-gray-700">{issue.description}</p>
              <p className="text-gray-500 mt-1">建议：{issue.suggestion}</p>
            </div>
          ))}
        </div>
      )}

      {report && report.issues.length === 0 && (
        <p className="text-green-600 text-sm">✓ 知识库状态良好，未发现问题。</p>
      )}
    </div>
  );
}
