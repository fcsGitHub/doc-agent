"use client";

import { ReviewResult } from "@/lib/types";
import { REVIEWER_NAMES } from "@/lib/constants";

interface ReviewerCardProps {
  result: ReviewResult;
  onClick?: () => void;
  isSelected?: boolean;
}

export function ReviewerCard({
  result,
  onClick,
  isSelected,
}: ReviewerCardProps) {
  const statusColors = {
    pass: "bg-green-100 text-green-800 border-green-200",
    fail: "bg-red-100 text-red-800 border-red-200",
    warning: "bg-yellow-100 text-yellow-800 border-yellow-200",
  };

  const statusLabels = {
    pass: "通过",
    fail: "未通过",
    warning: "警告",
  };

  const displayName =
    REVIEWER_NAMES[result.reviewer_name] || result.reviewer_name;

  return (
    <div
      onClick={onClick}
      className={`p-4 border rounded-lg cursor-pointer transition-all duration-200 ${
        isSelected ? "ring-2 ring-blue-500 shadow-md" : "hover:shadow-md"
      }`}
    >
      <div className="flex justify-between items-start mb-3">
        <h3 className="font-semibold text-gray-800">{displayName}</h3>
        <span
          className={`px-2 py-1 text-xs font-medium rounded-full border ${
            statusColors[result.status]
          }`}
        >
          {statusLabels[result.status]}
        </span>
      </div>
      <div className="flex justify-between items-center mt-4 text-sm text-gray-600">
        <div>
          <span>得分: </span>
          <span className="font-medium text-gray-900">
            {Math.round(result.score * 100)}/100
          </span>
        </div>
        <div>
          <span>问题: </span>
          <span
            className={`font-medium ${result.issues.length > 0 ? "text-red-600" : "text-gray-900"}`}
          >
            {result.issues.length}
          </span>
        </div>
      </div>
    </div>
  );
}
