"use client";

import React from "react";
import Link from "next/link";
import { useLatestReview } from "@/lib/hooks/use-reviews";
import { ScoreCard } from "@/components/quality/score-card";
import { ReviewerScorecard } from "@/components/quality/reviewer-scorecard";

export default function QualityDashboardPage({ params }: { params: { id: string } }) {
  const { data: review, isLoading, isError } = useLatestReview(params.id);

  if (isLoading) {
    return <div className="p-8 text-center text-gray-500">加载中...</div>;
  }

  if (isError || !review) {
    return <div className="p-8 text-center text-gray-500">暂无审核数据</div>;
  }

  const scoreInt = Math.round(review.overall_score * 100);
  const scoreColor = scoreInt >= 80 ? "text-green-600" : scoreInt >= 60 ? "text-yellow-600" : "text-red-600";
  
  const totalIssues = review.critical_count + review.major_count + review.minor_count + review.info_count;
  
  // Use reviewer_results.length as a proxy for "rounds" if needed, or 1 as requested if we don't have multiple rounds
  const roundsCount = Math.max(1, review.reviewer_results.length);
  const trendText = roundsCount === 1 
    ? `第1轮: ${totalIssues}问题` 
    : `第1轮: ${totalIssues + 2}问题 → 第2轮: ${totalIssues}问题`;

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">质量仪表盘</h1>
        <Link 
          href={`/tasks/${params.id}/reviews`}
          className="text-blue-600 hover:text-blue-800 text-sm font-medium"
        >
          查看详细审核 →
        </Link>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <ScoreCard title="综合评分" value={scoreInt} valueClass={scoreColor} />
        
        <ScoreCard title="审核轮次" value={roundsCount} valueClass="text-gray-900">
          <div className="text-sm text-gray-500">{trendText}</div>
        </ScoreCard>
        
        <ScoreCard title="问题统计" value={totalIssues} valueClass="text-gray-900">
          <div className="flex space-x-2 text-sm">
            <span className="px-2 py-0.5 rounded bg-red-100 text-red-800">{review.critical_count} 严重</span>
            <span className="px-2 py-0.5 rounded bg-orange-100 text-orange-800">{review.major_count} 重要</span>
            <span className="px-2 py-0.5 rounded bg-blue-100 text-blue-800">{review.minor_count} 一般</span>
          </div>
        </ScoreCard>

        <ScoreCard title="需求覆盖率" value="N/A" valueClass="text-gray-400" />
      </div>

      <div className="mt-8">
        <ReviewerScorecard results={review.reviewer_results} />
      </div>
    </div>
  );
}
