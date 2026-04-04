"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ExportChecklist } from "@/components/export/export-checklist";
import { apiFetch } from "@/lib/api";
import { useLatestReview } from "@/lib/hooks/use-reviews";
import { useSections } from "@/lib/hooks/use-document";
import type { Task } from "@/lib/types";

interface ExportPageProps {
  params: {
    id: string;
  };
}

export default function ExportPage({ params }: ExportPageProps) {
  const taskId = params.id;
  const { data: task, isLoading: isTaskLoading } = useQuery<Task>({
    queryKey: ["task", taskId],
    queryFn: () => apiFetch<Task>(`/api/v1/tasks/${taskId}`),
    enabled: !!taskId,
  });
  const { data: sections } = useSections(taskId);
  const { data: review } = useLatestReview(taskId);
  const [isDownloading, setIsDownloading] = useState(false);

  const allSectionsGenerated = useMemo(
    () =>
      !!sections?.length &&
      sections.every(
        (section) => section.status !== "pending" && section.status !== "generating",
      ),
    [sections],
  );

  const reviewsPassed =
    review?.overall_status === "approved" ||
    task?.status === "approved" ||
    task?.status === "completed";

  const finalApprovalCompleted =
    task?.status === "completed" || task?.status === "approved";

  const canExport =
    allSectionsGenerated && reviewsPassed && finalApprovalCompleted && !!task;

  const handleExport = async () => {
    if (!task || !canExport || isDownloading) return;

    setIsDownloading(true);
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/tasks/${taskId}/export/docx`,
      );
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${task.name}.docx`;
      a.click();
      URL.revokeObjectURL(url);
    } finally {
      setIsDownloading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 px-6 py-8">
      <div className="mx-auto max-w-3xl space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <Link href={`/tasks/${taskId}`} className="text-sm text-blue-600 hover:underline">
              ← 返回工作台
            </Link>
            <h1 className="mt-2 text-2xl font-bold text-gray-900">
              {task?.name ?? "导出 DOCX"}
            </h1>
            <p className="mt-1 text-sm text-gray-500">
              {isTaskLoading ? "任务信息加载中..." : "导出前请确认所有条件已满足"}
            </p>
          </div>
        </div>

        <ExportChecklist
          sectionsGenerated={allSectionsGenerated}
          reviewsPassed={reviewsPassed}
          finalApprovalCompleted={finalApprovalCompleted}
        />

        <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
          <button
            type="button"
            onClick={handleExport}
            disabled={!canExport || isDownloading}
            className="rounded-md bg-blue-600 px-5 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isDownloading ? "导出中..." : "导出 DOCX"}
          </button>
        </div>
      </div>
    </div>
  );
}
