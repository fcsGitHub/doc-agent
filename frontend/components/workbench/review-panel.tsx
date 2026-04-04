"use client";

import { useState } from "react";
import { useSSE } from "@/lib/hooks/use-sse";
import { useTask } from "@/lib/hooks/use-document";
import {
  useLatestReview,
  useRunReviews,
  useSubmitApproval,
} from "@/lib/hooks/use-reviews";
import type { TaskStatus } from "@/lib/types";

const PIPELINE_PHASES = [
  "parsing",
  "extracting",
  "planning",
  "awaiting_outline_approval",
  "generating",
  "reviewing",
  "revising",
  "awaiting_approval",
  "approved",
  "completed",
];

function getStepStatus(
  stepPhase: string,
  taskStatus: TaskStatus,
): "done" | "current" | "pending" {
  const currentIdx = PIPELINE_PHASES.indexOf(taskStatus);
  const stepIdx = PIPELINE_PHASES.indexOf(stepPhase);
  if (currentIdx === -1) return "pending";
  if (stepIdx < currentIdx) return "done";
  if (stepIdx === currentIdx) return "current";
  return "pending";
}

const STEPS = [
  { label: "解析文档", phase: "parsing" },
  { label: "提取需求", phase: "extracting" },
  { label: "规划大纲", phase: "planning" },
  { label: "审批大纲", phase: "awaiting_outline_approval" },
  { label: "生成内容", phase: "generating" },
  { label: "运行审核", phase: "reviewing" },
  { label: "修订内容", phase: "revising" },
  { label: "最终审批", phase: "awaiting_approval" },
];

export function ReviewPanel({ taskId }: { taskId: string }) {
  const { data: task } = useTask(taskId);
  const { data: reviewData } = useLatestReview(taskId);
  const runReviews = useRunReviews(taskId);
  const submitApproval = useSubmitApproval(taskId);
  const sse = useSSE(taskId);

  const [isIssuesExpanded, setIsIssuesExpanded] = useState(false);

  const taskStatus = task?.status || "created";

  const renderStatusIcon = (status: "done" | "current" | "pending") => {
    if (status === "done") {
      return (
        <div className="w-5 h-5 flex items-center justify-center rounded-full bg-green-100 text-green-600 text-xs shrink-0">
          ✓
        </div>
      );
    }
    if (status === "current") {
      return (
        <div className="w-5 h-5 flex items-center justify-center rounded-full bg-blue-100 text-blue-600 text-[10px] shrink-0">
          ▶
        </div>
      );
    }
    return (
      <div className="w-5 h-5 flex items-center justify-center rounded-full bg-gray-100 text-gray-400 text-xs shrink-0">
        ·
      </div>
    );
  };

  const getOverallStatusLabel = (status: string) => {
    switch (status) {
      case "approved":
        return "通过";
      case "needs_revision":
        return "需修订";
      case "rejected":
        return "拒绝";
      default:
        return "未知";
    }
  };

  const getOverallStatusColor = (status: string) => {
    switch (status) {
      case "approved":
        return "bg-green-100 text-green-800";
      case "needs_revision":
        return "bg-yellow-100 text-yellow-800";
      case "rejected":
        return "bg-red-100 text-red-800";
      default:
        return "bg-gray-100 text-gray-800";
    }
  };

  const scoreDisplay = reviewData
    ? Math.floor(reviewData.overall_score * 100)
    : 0;

  return (
    <div className="h-full flex flex-col bg-white border-l border-gray-200">
      <div className="p-4 border-b border-gray-200 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-800">审核与进度</h2>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-8">
        {/* Progress Steps */}
        <section>
          <h3 className="text-sm font-medium text-gray-500 mb-4 uppercase tracking-wider">
            流水线进度
          </h3>
          <div className="space-y-4">
            {STEPS.map((step, idx) => {
              const status = getStepStatus(step.phase, taskStatus);
              return (
                <div key={idx} className="flex items-center space-x-3">
                  {renderStatusIcon(status)}
                  <span
                    className={`text-sm ${
                      status === "current"
                        ? "text-blue-700 font-medium"
                        : status === "done"
                          ? "text-gray-700"
                          : "text-gray-400"
                    }`}
                  >
                    {step.label}
                  </span>
                </div>
              );
            })}
          </div>
        </section>

        {/* Review Summary */}
        {reviewData && (
          <section>
            <h3 className="text-sm font-medium text-gray-500 mb-4 uppercase tracking-wider">
              审核摘要
            </h3>
            <div className="bg-gray-50 rounded-lg p-4 space-y-4 border border-gray-100">
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-600">
                  综合评分: {scoreDisplay}/100
                </span>
                <span
                  className={`px-2 py-1 rounded-full text-xs font-medium ${getOverallStatusColor(
                    reviewData.overall_status,
                  )}`}
                >
                  {getOverallStatusLabel(reviewData.overall_status)}
                </span>
              </div>
              <div className="flex flex-wrap gap-2">
                <span className="px-2 py-1 bg-red-50 text-red-700 rounded text-xs border border-red-100">
                  严重:{reviewData.critical_count}
                </span>
                <span className="px-2 py-1 bg-orange-50 text-orange-700 rounded text-xs border border-orange-100">
                  重要:{reviewData.major_count}
                </span>
                <span className="px-2 py-1 bg-blue-50 text-blue-700 rounded text-xs border border-blue-100">
                  建议:{reviewData.minor_count}
                </span>
              </div>

              {reviewData.issues && reviewData.issues.length > 0 && (
                <div>
                  <button
                    onClick={() => setIsIssuesExpanded(!isIssuesExpanded)}
                    className="text-xs text-blue-600 hover:text-blue-800 flex items-center"
                  >
                    {isIssuesExpanded ? "收起问题列表" : "展开问题列表"}
                  </button>
                  {isIssuesExpanded && (
                    <div className="mt-3 space-y-2 max-h-48 overflow-y-auto pr-1">
                      {reviewData.issues.map((issue) => (
                        <div
                          key={issue.id}
                          className="bg-white p-2 rounded border border-gray-200 text-xs space-y-1"
                        >
                          <div className="flex items-center justify-between">
                            <span
                              className={`font-semibold ${
                                issue.severity === "critical"
                                  ? "text-red-700"
                                  : issue.severity === "major"
                                    ? "text-orange-700"
                                    : issue.severity === "minor"
                                      ? "text-blue-700"
                                      : "text-gray-600"
                              }`}
                            >
                              [{issue.severity}]
                            </span>
                          </div>
                          <p className="text-gray-700 leading-relaxed">
                            {issue.description}
                          </p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </section>
        )}
      </div>

      {/* Action Buttons */}
      <div className="p-4 border-t border-gray-200 bg-gray-50 flex flex-col gap-3">
        {(taskStatus === "awaiting_approval" || reviewData) && (
          <div className="flex gap-3">
            <button
              onClick={() => submitApproval.mutate({ approved: true })}
              disabled={submitApproval.isPending}
              className="flex-1 py-2 px-4 bg-green-600 text-white rounded text-sm font-medium hover:bg-green-700 disabled:opacity-50 transition-colors"
            >
              {submitApproval.isPending ? "提交中..." : "批准"}
            </button>
            <button
              onClick={() => submitApproval.mutate({ approved: false })}
              disabled={submitApproval.isPending}
              className="flex-1 py-2 px-4 bg-yellow-600 text-white rounded text-sm font-medium hover:bg-yellow-700 disabled:opacity-50 transition-colors"
            >
              {submitApproval.isPending ? "提交中..." : "需要修改"}
            </button>
          </div>
        )}
        <button
          onClick={() => runReviews.mutate()}
          disabled={runReviews.isPending}
          className="w-full py-2 px-4 bg-white border border-gray-300 text-gray-700 rounded text-sm font-medium hover:bg-gray-50 disabled:opacity-50 transition-colors"
        >
          {runReviews.isPending ? "运行中..." : "运行审核"}
        </button>
      </div>
    </div>
  );
}
