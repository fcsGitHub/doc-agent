"use client";

import { useMemo } from "react";
import Link from "next/link";
import { ReviewerCard } from "@/components/review/reviewer-card";
import { IssueTable } from "@/components/review/issue-table";
import { RevisionTimeline } from "@/components/review/revision-timeline";
import { useLatestReview } from "@/lib/hooks/use-reviews";

interface ReviewDashboardPageProps {
  params: {
    id: string;
  };
}

export default function ReviewDashboardPage({
  params,
}: ReviewDashboardPageProps) {
  const taskId = params.id;
  const { data: review, isLoading, isError } = useLatestReview(taskId);

  const statusColors = {
    approved: "bg-green-100 text-green-800",
    needs_revision: "bg-yellow-100 text-yellow-800",
    rejected: "bg-red-100 text-red-800",
  };

  const statusLabels = {
    approved: "通过",
    needs_revision: "需要修改",
    rejected: "已拒绝",
  };

  const allIssues = useMemo(() => {
    if (!review) return [];

    // Combine top-level issues and reviewer-specific issues
    const combined = [
      ...review.issues.map((issue) => ({ ...issue, reviewer_name: undefined })),
    ];

    review.reviewer_results.forEach((result) => {
      result.issues.forEach((issue) => {
        combined.push({
          ...issue,
          reviewer_name: result.reviewer_name as any,
        });
      });
    });

    // Remove duplicates by ID just in case
    const seen = new Set();
    return combined.filter((issue) => {
      if (seen.has(issue.id)) return false;
      seen.add(issue.id);
      return true;
    });
  }, [review]);

  // Mock revision history based on the current review
  const mockRounds = useMemo(() => {
    if (!review) return [];
    return [
      {
        id: "round-1",
        round_number: 1,
        created_at: new Date().toISOString(),
        status: review.overall_status,
        issue_count: allIssues.length,
      },
    ];
  }, [review, allIssues.length]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-gray-500">加载中...</div>
      </div>
    );
  }

  if (isError || !review) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center flex-col">
        <div className="text-red-500 mb-4">加载失败或无审核数据</div>
        <Link
          href={`/tasks/${taskId}`}
          className="text-blue-600 hover:underline"
        >
          ← 返回工作台
        </Link>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-white border-b px-6 py-4 flex items-center justify-between sticky top-0 z-10">
        <div className="flex items-center space-x-4">
          <Link
            href={`/tasks/${taskId}`}
            className="text-gray-500 hover:text-gray-800 transition-colors flex items-center font-medium"
          >
            <span className="mr-1">←</span> 返回工作台
          </Link>
          <div className="h-6 w-px bg-gray-300"></div>
          <h1 className="text-xl font-bold text-gray-900">审核面板</h1>
          <span
            className={`px-2.5 py-1 text-sm font-medium rounded-full ${statusColors[review.overall_status]}`}
          >
            {statusLabels[review.overall_status]}
          </span>
        </div>

        <div className="flex items-center space-x-6 text-sm">
          <div className="flex flex-col items-end">
            <span className="text-gray-500">综合得分</span>
            <span className="font-bold text-lg text-gray-900">
              {Math.round(review.overall_score * 100)}
              <span className="text-sm font-normal text-gray-500">/100</span>
            </span>
          </div>
          <div className="flex space-x-3">
            <div className="flex flex-col items-center">
              <span className="text-red-600 font-bold text-lg">
                {review.critical_count}
              </span>
              <span className="text-xs text-gray-500">严重</span>
            </div>
            <div className="flex flex-col items-center">
              <span className="text-orange-500 font-bold text-lg">
                {review.major_count}
              </span>
              <span className="text-xs text-gray-500">重要</span>
            </div>
            <div className="flex flex-col items-center">
              <span className="text-blue-600 font-bold text-lg">
                {review.minor_count}
              </span>
              <span className="text-xs text-gray-500">建议</span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl mx-auto w-full p-6 grid grid-cols-12 gap-6">
        {/* Left Column: Reviewers & Issues (9 cols) */}
        <div className="col-span-12 lg:col-span-9 space-y-6">
          <section>
            <h2 className="text-lg font-semibold text-gray-800 mb-4">
              审核结果
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {review.reviewer_results.map((result) => (
                <ReviewerCard key={result.reviewer_name} result={result} />
              ))}
            </div>
          </section>

          <section>
            <IssueTable issues={allIssues} />
          </section>
        </div>

        {/* Right Column: Timeline (3 cols) */}
        <div className="col-span-12 lg:col-span-3">
          <div className="bg-white rounded-lg shadow border p-5 sticky top-24">
            <h2 className="text-lg font-semibold text-gray-800 mb-6">
              审核历史
            </h2>
            <RevisionTimeline rounds={mockRounds as any} />
          </div>
        </div>
      </main>
    </div>
  );
}
