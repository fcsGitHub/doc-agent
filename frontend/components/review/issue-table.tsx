"use client";

import { useState, useMemo } from "react";
import { ReviewIssue } from "@/lib/types";

const REVIEWER_NAMES: Record<string, string> = {
  structure: "格式审核",
  compliance: "合规审核",
  technical: "技术审核",
  evidence: "证据审核",
  consistency: "一致性审核",
  style: "风格审核",
  coverage: "覆盖率审核",
  risk: "风险审核",
};

interface IssueWithReviewer extends ReviewIssue {
  reviewer_name?: string;
}

interface IssueTableProps {
  issues: IssueWithReviewer[];
}

export function IssueTable({ issues }: IssueTableProps) {
  const [filter, setFilter] = useState<"all" | "critical" | "major" | "minor">(
    "all",
  );

  const severityLabels = {
    critical: "严重",
    major: "重要",
    minor: "建议",
    info: "信息",
  };

  const severityColors = {
    critical: "bg-red-100 text-red-800",
    major: "bg-orange-100 text-orange-800",
    minor: "bg-blue-100 text-blue-800",
    info: "bg-gray-100 text-gray-800",
  };

  const filteredAndSortedIssues = useMemo(() => {
    let filtered = issues;
    if (filter !== "all") {
      filtered = issues.filter((issue) => issue.severity === filter);
    }

    // Sort: critical > major > minor > info
    const severityOrder = { critical: 0, major: 1, minor: 2, info: 3 };
    return [...filtered].sort(
      (a, b) => severityOrder[a.severity] - severityOrder[b.severity],
    );
  }, [issues, filter]);

  return (
    <div className="bg-white rounded-lg shadow border overflow-hidden">
      <div className="p-4 border-b flex justify-between items-center bg-gray-50">
        <h3 className="font-semibold text-gray-800">审核问题列表</h3>
        <div className="flex space-x-2">
          {(["all", "critical", "major", "minor"] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1 text-sm rounded-full transition-colors ${
                filter === f
                  ? "bg-blue-600 text-white"
                  : "bg-white text-gray-600 border hover:bg-gray-50"
              }`}
            >
              {f === "all"
                ? "全部"
                : severityLabels[f as keyof typeof severityLabels]}
            </button>
          ))}
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm text-left">
          <thead className="text-xs text-gray-700 uppercase bg-gray-50">
            <tr>
              <th className="px-6 py-3 font-medium">审核员</th>
              <th className="px-6 py-3 font-medium">严重程度</th>
              <th className="px-6 py-3 font-medium">类别</th>
              <th className="px-6 py-3 font-medium">位置</th>
              <th className="px-6 py-3 font-medium">描述</th>
              <th className="px-6 py-3 font-medium">建议</th>
            </tr>
          </thead>
          <tbody>
            {filteredAndSortedIssues.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-6 py-8 text-center text-gray-500">
                  没有找到符合条件的问题
                </td>
              </tr>
            ) : (
              filteredAndSortedIssues.map((issue) => (
                <tr key={issue.id} className="border-b hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap text-gray-700 font-medium">
                    {issue.reviewer_name
                      ? REVIEWER_NAMES[issue.reviewer_name] ||
                        issue.reviewer_name
                      : "综合审核"}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span
                      className={`px-2 py-1 rounded text-xs font-medium ${severityColors[issue.severity]}`}
                    >
                      {severityLabels[issue.severity]}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-gray-600">
                    {issue.requires_human ? "人工确认" : "自动检测"}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-gray-600">
                    {issue.section_id || "全局"}
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-gray-800">{issue.description}</div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="text-gray-600">-</div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
