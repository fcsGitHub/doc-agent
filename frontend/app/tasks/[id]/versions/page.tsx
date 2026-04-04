"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useTask, useSections } from "@/lib/hooks/use-document";
import { useRollback } from "@/lib/hooks/use-versions";
import { VersionList } from "@/components/version/version-list";
import { DiffViewer } from "@/components/version/diff-viewer";

interface VersionsPageProps {
  params: {
    id: string;
  };
}

export default function VersionsPage({ params }: VersionsPageProps) {
  const taskId = params.id;
  const { data: task, isLoading: isTaskLoading } = useTask(taskId);
  const { data: sections, isLoading: isSectionsLoading } = useSections(taskId);

  const [selectedSectionId, setSelectedSectionId] = useState<string | null>(
    null,
  );
  const [selectedVersionA, setSelectedVersionA] = useState<string | null>(null);
  const [selectedVersionB, setSelectedVersionB] = useState<string | null>(null);

  // Initialize selectedSectionId when sections are loaded
  React.useEffect(() => {
    if (sections && sections.length > 0 && !selectedSectionId) {
      setSelectedSectionId(sections[0].id);
    }
  }, [sections, selectedSectionId]);

  // When section changes, reset selected versions
  const handleSectionChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedSectionId(e.target.value);
    setSelectedVersionA(null);
    setSelectedVersionB(null);
  };

  const { mutate: rollback } = useRollback(selectedSectionId || "");

  if (isTaskLoading || isSectionsLoading) {
    return <div className="p-8 text-center text-gray-500">加载中...</div>;
  }

  if (!task) {
    return <div className="p-8 text-center text-red-500">找不到任务</div>;
  }

  return (
    <div className="flex flex-col h-screen overflow-hidden bg-gray-50">
      {/* Top Bar */}
      <header className="h-16 bg-white border-b flex items-center justify-between px-6 shrink-0">
        <div className="flex items-center gap-4">
          <Link
            href={`/tasks/${taskId}`}
            className="text-gray-500 hover:text-gray-800 transition-colors"
          >
            ← 返回工作台
          </Link>
          <h1 className="text-xl font-semibold text-gray-800">
            版本历史 — {task.name}
          </h1>
        </div>
        <div className="flex items-center gap-2">
          <label
            htmlFor="section-select"
            className="text-sm font-medium text-gray-700"
          >
            选择章节:
          </label>
          <select
            id="section-select"
            className="border rounded p-1.5 text-sm"
            value={selectedSectionId || ""}
            onChange={handleSectionChange}
          >
            {sections?.map((sec) => (
              <option key={sec.id} value={sec.id}>
                {sec.title}
              </option>
            ))}
          </select>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 overflow-hidden">
        {selectedSectionId ? (
          <div className="grid grid-cols-[350px_1fr] h-full">
            {/* Left Panel: Version List */}
            <VersionList
              sectionId={selectedSectionId}
              selectedVersionA={selectedVersionA}
              selectedVersionB={selectedVersionB}
              onSelectA={setSelectedVersionA}
              onSelectB={setSelectedVersionB}
              onRollback={rollback}
            />

            {/* Right Panel: Diff Viewer */}
            <DiffViewer
              versionAId={selectedVersionA}
              versionBId={selectedVersionB}
            />
          </div>
        ) : (
          <div className="flex items-center justify-center h-full text-gray-500">
            任务中没有可用的章节
          </div>
        )}
      </main>
    </div>
  );
}
