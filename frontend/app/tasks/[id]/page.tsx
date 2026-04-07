"use client";

import { useState } from "react";
import { OutlinePanel } from "@/components/workbench/outline-panel";
import { ContentPanel } from "@/components/workbench/content-panel";
import { ReviewPanel } from "@/components/workbench/review-panel";
import { useTask, useStartTask } from "@/lib/hooks/use-document";
import { ChatSidebar } from "@/components/chat/chat-sidebar";

interface WorkbenchPageProps {
  params: {
    id: string;
  };
}

export default function WorkbenchPage({ params }: WorkbenchPageProps) {
  const taskId = params.id;
  const [selectedSectionId, setSelectedSectionId] = useState<string | null>(
    null,
  );

  const { data: task, isLoading, isError } = useTask(taskId);
  const { mutate: startTask, isPending: isStarting } = useStartTask(taskId);

  if (isLoading) {
    return <div className="p-8 text-center">加载中...</div>;
  }

  if (isError || !task) {
    return <div className="p-8 text-center text-red-500">加载失败</div>;
  }

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-gray-50">
      {/* Top Bar */}
      <header className="h-16 bg-white border-b flex items-center justify-between px-6 shrink-0">
        <h1 className="text-xl font-semibold text-gray-800">
          工作台 — {task.name}
        </h1>
        {task.status === "created" && (
          <button
            onClick={() => startTask()}
            disabled={isStarting}
            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded font-medium disabled:opacity-50"
          >
            {isStarting ? "处理中..." : "开始处理"}
          </button>
        )}
      </header>

      {/* Main Content Area */}
      <main className="flex-1 overflow-hidden">
        <div className="grid grid-cols-[280px_1fr_320px] h-[calc(100vh-4rem)]">
          {/* Left Panel: Outline */}
          <OutlinePanel
            taskId={taskId}
            onSectionSelect={setSelectedSectionId}
          />

          {/* Center Panel: Content */}
          <ContentPanel taskId={taskId} sectionId={selectedSectionId} />

          {/* Right Panel: Review & Progress */}
          <ReviewPanel taskId={taskId} />
        </div>
      </main>
      <ChatSidebar taskId={taskId} />
    </div>
  );
}
