"use client";

import React, { useState, useMemo } from "react";
import { useSection } from "@/lib/hooks/use-document";
import { useLatestReview } from "@/lib/hooks/use-reviews";
import { SectionContent } from "./section-content";
import { GenerationProgress } from "./generation-progress";
import { AnnotationOverlay } from "./annotation-overlay";

interface ContentPanelProps {
  taskId: string;
  sectionId: string | null;
}

export function ContentPanel({ taskId, sectionId }: ContentPanelProps) {
  const { data: section, isLoading, isError } = useSection(taskId, sectionId);
  const { data: reviewData } = useLatestReview(taskId);
  const [showAnnotations, setShowAnnotations] = useState(false);

  const sectionIssues = useMemo(() => {
    if (!reviewData?.issues || !sectionId) return [];
    return reviewData.issues.filter(issue => issue.section_id === sectionId);
  }, [reviewData?.issues, sectionId]);

  if (!sectionId) {
    return (
      <div className="flex-1 bg-gray-50 flex items-center justify-center border-r h-full">
        <div className="text-gray-400 text-lg">选择左侧章节查看内容</div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex-1 bg-white flex items-center justify-center border-r h-full">
        <div className="text-gray-400">加载中...</div>
      </div>
    );
  }

  if (isError || !section) {
    return (
      <div className="flex-1 bg-white flex items-center justify-center border-r h-full">
        <div className="text-red-500">加载章节失败</div>
      </div>
    );
  }

  return (
    <div className="flex-1 bg-white flex flex-col border-r h-full overflow-hidden relative">
      <div className="absolute top-0 left-0 right-0 z-10">
        <GenerationProgress status={section.status} />
      </div>
      
      {/* Action Bar for toggle */}
      <div className="flex justify-end p-2 bg-white border-b z-20">
        <button
          onClick={() => setShowAnnotations(!showAnnotations)}
          className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
            showAnnotations 
              ? "bg-blue-100 text-blue-700 border border-blue-200" 
              : "bg-gray-100 text-gray-700 border border-gray-200 hover:bg-gray-200"
          }`}
        >
          {showAnnotations ? "隐藏审核标注" : "显示审核标注"}
        </button>
      </div>

      <div className="flex-1 overflow-hidden relative">
        <SectionContent section={section}>
          {showAnnotations ? (
            <AnnotationOverlay 
              content={section.content || ""} 
              issues={sectionIssues} 
              visible={showAnnotations} 
            />
          ) : undefined}
        </SectionContent>
      </div>
    </div>
  );
}

