import React from "react";
import type { ReviewIssue } from "@/lib/types";

// Extended interface since the prompt mentions these fields
export interface ExtendedReviewIssue extends ReviewIssue {
  category?: string;
  suggestion?: string;
  location_excerpt?: string;
  reviewer_name?: string;
}

interface IssuePopoverProps {
  issue: ExtendedReviewIssue;
  onClose: () => void;
  onPrev?: () => void;
  onNext?: () => void;
  hasPrev?: boolean;
  hasNext?: boolean;
}

export function IssuePopover({ issue, onClose, onPrev, onNext, hasPrev, hasNext }: IssuePopoverProps) {
  const getSeverityBadge = (severity: string) => {
    switch (severity) {
      case "critical": return <span className="px-2 py-0.5 rounded text-xs font-bold bg-red-100 text-red-700">致命</span>;
      case "major": return <span className="px-2 py-0.5 rounded text-xs font-bold bg-orange-100 text-orange-700">严重</span>;
      case "minor": return <span className="px-2 py-0.5 rounded text-xs font-bold bg-yellow-100 text-yellow-700">一般</span>;
      case "info": return <span className="px-2 py-0.5 rounded text-xs font-bold bg-blue-100 text-blue-700">提示</span>;
      default: return <span className="px-2 py-0.5 rounded text-xs font-bold bg-gray-100 text-gray-700">未知</span>;
    }
  };

  return (
    <div className="absolute top-4 right-4 w-80 bg-white shadow-xl border border-gray-200 rounded-lg z-50 flex flex-col" data-testid="issue-popover">
      <div className="flex items-center justify-between p-3 border-b border-gray-100 bg-gray-50 rounded-t-lg">
        <div className="flex items-center gap-2">
          {getSeverityBadge(issue.severity)}
          <span className="text-sm font-medium text-gray-700">{issue.category || "未分类"}</span>
        </div>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-600 transition-colors" data-testid="close-popover">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
        </button>
      </div>
      
      <div className="p-4 flex-1 overflow-y-auto max-h-[60vh]">
        {issue.reviewer_name && (
          <div className="mb-3 text-sm text-gray-500 flex items-center gap-1">
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
            审核人: {issue.reviewer_name}
          </div>
        )}
        
        <div className="mb-4">
          <h4 className="text-xs font-semibold text-gray-400 uppercase mb-1">问题描述</h4>
          <p className="text-sm text-gray-800 whitespace-pre-wrap">{issue.description}</p>
        </div>
        
        {issue.suggestion && (
          <div>
            <h4 className="text-xs font-semibold text-gray-400 uppercase mb-1">修改建议</h4>
            <p className="text-sm text-gray-800 whitespace-pre-wrap bg-blue-50 p-2 rounded border border-blue-100">{issue.suggestion}</p>
          </div>
        )}
      </div>
      
      {(hasPrev || hasNext) && (
        <div className="flex items-center justify-between p-3 border-t border-gray-100 bg-gray-50 rounded-b-lg">
          <button 
            onClick={onPrev} 
            disabled={!hasPrev}
            className={`text-sm px-2 py-1 flex items-center gap-1 ${!hasPrev ? "text-gray-300 cursor-not-allowed" : "text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded transition-colors"}`}
          >
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6"/></svg>
            上一个问题
          </button>
          <button 
            onClick={onNext} 
            disabled={!hasNext}
            className={`text-sm px-2 py-1 flex items-center gap-1 ${!hasNext ? "text-gray-300 cursor-not-allowed" : "text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded transition-colors"}`}
          >
            下一个问题
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m9 18 6-6-6-6"/></svg>
          </button>
        </div>
      )}
    </div>
  );
}

