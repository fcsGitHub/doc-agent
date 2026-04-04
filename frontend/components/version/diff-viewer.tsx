import React from "react";
import { useDiff } from "@/lib/hooks/use-versions";

interface DiffViewerProps {
  versionAId: string | null;
  versionBId: string | null;
}

export function DiffViewer({ versionAId, versionBId }: DiffViewerProps) {
  const { data: diff, isLoading, isError } = useDiff(versionAId, versionBId);

  if (!versionAId || !versionBId) {
    return (
      <div className="flex-1 flex items-center justify-center bg-gray-50 h-full">
        <div className="text-gray-500 text-lg">请选择两个版本进行对比</div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center bg-white h-full">
        <div className="text-gray-500">正在对比版本差异...</div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex-1 flex items-center justify-center bg-white h-full">
        <div className="text-red-500">对比失败</div>
      </div>
    );
  }

  if (!diff || !diff.hunks || diff.hunks.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center bg-white h-full">
        <div className="text-gray-500">这两个版本没有差异</div>
      </div>
    );
  }

  return (
    <div className="flex-1 bg-white overflow-y-auto font-mono text-sm leading-relaxed p-4">
      {diff.hunks.map((hunk, hIdx) => (
        <div
          key={hIdx}
          className="mb-4 border border-gray-200 rounded overflow-hidden"
        >
          <div className="bg-gray-100 text-gray-500 px-4 py-1 border-b border-gray-200">
            差异片段 {hIdx + 1}
          </div>
          <div className="bg-white">
            {hunk.lines.map((line, lIdx) => {
              let bgColor = "";
              let textColor = "";
              let prefix = "  ";
              let textDecoration = "";

              if (line.type === "add") {
                bgColor = "bg-green-100";
                textColor = "text-green-800";
                prefix = "+ ";
              } else if (line.type === "delete") {
                bgColor = "bg-red-100";
                textColor = "text-red-800";
                prefix = "- ";
                textDecoration = "line-through";
              } else {
                bgColor = "bg-white";
                textColor = "text-gray-700";
              }

              return (
                <div
                  key={lIdx}
                  className={`flex px-2 py-0.5 ${bgColor} ${textColor}`}
                >
                  <div className="w-12 text-right text-gray-400 select-none mr-4 text-xs pr-2 border-r border-gray-300">
                    {line.line_number}
                  </div>
                  <div className="whitespace-pre-wrap w-full">
                    <span className="select-none inline-block w-4 font-bold">
                      {prefix}
                    </span>
                    <span className={textDecoration}>{line.content}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
