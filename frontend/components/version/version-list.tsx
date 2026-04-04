import React from "react";
import { useVersions } from "@/lib/hooks/use-versions";

interface VersionListProps {
  sectionId: string;
  selectedVersionA: string | null;
  selectedVersionB: string | null;
  onSelectA: (id: string) => void;
  onSelectB: (id: string) => void;
  onRollback: (versionId: string) => void;
}

const SOURCE_LABELS: Record<string, string> = {
  generated: "生成",
  revised: "修订",
  manual: "手动",
};

export function VersionList({
  sectionId,
  selectedVersionA,
  selectedVersionB,
  onSelectA,
  onSelectB,
  onRollback,
}: VersionListProps) {
  const { data: versions, isLoading, isError } = useVersions(sectionId);

  if (isLoading) {
    return <div className="p-4 text-gray-500">加载版本历史...</div>;
  }

  if (isError) {
    return <div className="p-4 text-red-500">加载失败</div>;
  }

  if (!versions || versions.length === 0) {
    return <div className="p-4 text-gray-500">暂无版本历史</div>;
  }

  return (
    <div className="flex flex-col h-full bg-white border-r overflow-y-auto">
      <div className="p-4 font-medium border-b sticky top-0 bg-white z-10">
        版本历史
      </div>
      <div className="flex-1 overflow-y-auto p-2 space-y-2">
        {versions.map((version) => {
          const isA = selectedVersionA === version.id;
          const isB = selectedVersionB === version.id;

          return (
            <div
              key={version.id}
              className={`p-3 border rounded-lg hover:border-blue-300 transition-colors ${
                isA
                  ? "border-blue-500 bg-blue-50"
                  : isB
                    ? "border-green-500 bg-green-50"
                    : "border-gray-200"
              }`}
            >
              <div className="flex justify-between items-start mb-2">
                <div className="font-medium text-sm">
                  版本 {version.version_number}
                </div>
                <span className="text-xs px-2 py-1 bg-gray-100 rounded text-gray-600">
                  {SOURCE_LABELS[version.change_source] ||
                    version.change_source}
                </span>
              </div>

              <div className="text-xs text-gray-500 mb-3">
                {new Date(version.created_at).toLocaleString()}
              </div>

              <div className="flex flex-col gap-2">
                <div className="flex gap-2">
                  <label className="text-xs flex items-center cursor-pointer">
                    <input
                      type="radio"
                      name="versionA"
                      className="mr-1"
                      checked={isA}
                      onChange={() => onSelectA(version.id)}
                    />
                    对比版本A
                  </label>
                  <label className="text-xs flex items-center cursor-pointer">
                    <input
                      type="radio"
                      name="versionB"
                      className="mr-1"
                      checked={isB}
                      onChange={() => onSelectB(version.id)}
                    />
                    对比版本B
                  </label>
                </div>

                <button
                  onClick={() => {
                    if (
                      window.confirm(
                        "确定要回滚到此版本吗？这将创建一个新的版本。",
                      )
                    ) {
                      onRollback(version.id);
                    }
                  }}
                  className="text-xs px-3 py-1.5 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded transition-colors w-full"
                >
                  回滚到此版本
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
