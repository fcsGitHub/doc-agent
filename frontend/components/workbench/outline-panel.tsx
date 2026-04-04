"use client";

import {
  useTask,
  useSections,
  useApproveOutline,
} from "@/lib/hooks/use-document";

interface OutlinePanelProps {
  taskId: string;
  onSectionSelect?: (id: string) => void;
}

export function OutlinePanel({ taskId, onSectionSelect }: OutlinePanelProps) {
  const {
    data: task,
    isLoading: isLoadingTask,
    isError: isErrorTask,
  } = useTask(taskId);
  const {
    data: sections,
    isLoading: isLoadingSections,
    isError: isErrorSections,
  } = useSections(taskId);
  const { mutate: approveOutline, isPending: isApproving } =
    useApproveOutline(taskId);

  if (isLoadingTask || isLoadingSections) {
    return <div className="p-4">加载中...</div>;
  }

  if (isErrorTask || isErrorSections) {
    return <div className="p-4 text-red-500">加载失败</div>;
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "completed":
        return "✓";
      case "generating":
        return "⟳";
      case "failed":
        return "✗";
      default:
        return "·";
    }
  };

  return (
    <div className="flex flex-col h-full bg-white border-r">
      <div className="p-4 border-b font-semibold text-lg">大纲结构</div>

      <div className="flex-1 overflow-y-auto p-2">
        {sections && sections.length > 0 ? (
          <ul className="space-y-1">
            {sections.map((section) => (
              <li
                key={section.id}
                className="flex items-center px-2 py-1.5 hover:bg-gray-100 rounded text-sm cursor-pointer"
                style={{ paddingLeft: `${(section.level - 1) * 1.5 + 0.5}rem` }}
                onClick={() => onSectionSelect?.(section.id)}
              >
                <span className="w-5 text-center mr-1 text-gray-500">
                  {getStatusIcon(section.status)}
                </span>
                <span className="truncate">{section.title}</span>
              </li>
            ))}
          </ul>
        ) : (
          <div className="text-gray-400 text-sm p-2">暂无大纲</div>
        )}
      </div>

      {task?.status === "awaiting_outline_approval" && (
        <div className="p-4 border-t">
          <button
            onClick={() => approveOutline()}
            disabled={isApproving}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white py-2 px-4 rounded font-medium disabled:opacity-50"
          >
            {isApproving ? "处理中..." : "审批大纲"}
          </button>
        </div>
      )}
    </div>
  );
}
