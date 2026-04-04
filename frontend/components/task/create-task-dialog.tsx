"use client";

import { FormEvent, useState } from "react";
import { useCreateTask } from "@/lib/hooks/use-tasks";

interface CreateTaskDialogProps {
  open: boolean;
  onClose: () => void;
}

export function CreateTaskDialog({ open, onClose }: CreateTaskDialogProps) {
  const [name, setName] = useState("");
  const [docType, setDocType] = useState("bid_document");
  const [file, setFile] = useState<File | undefined>(undefined);
  const { mutate, isPending } = useCreateTask();

  if (!open) {
    return null;
  }

  const handleSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();

    mutate(
      {
        name,
        doc_type: docType,
        file,
      },
      {
        onSuccess: () => {
          setName("");
          setDocType("bid_document");
          setFile(undefined);
          onClose();
        },
      },
    );
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      role="dialog"
      aria-modal="true"
      aria-label="新建任务"
    >
      <div className="w-full max-w-md rounded-lg bg-white p-5 shadow-xl">
        <h2 className="mb-4 text-lg font-semibold text-gray-900">新建任务</h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label
              htmlFor="task-name"
              className="mb-1 block text-sm font-medium text-gray-700"
            >
              任务名称
            </label>
            <input
              id="task-name"
              type="text"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm outline-none ring-blue-500 focus:ring-2"
            />
          </div>

          <div>
            <label
              htmlFor="task-doc-type"
              className="mb-1 block text-sm font-medium text-gray-700"
            >
              文档类型
            </label>
            <select
              id="task-doc-type"
              value={docType}
              onChange={(e) => setDocType(e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm outline-none ring-blue-500 focus:ring-2"
            >
              <option value="bid_document">投标书</option>
              <option value="technical_proposal">技术方案</option>
              <option value="feasibility_report">可行性报告</option>
            </select>
          </div>

          <div>
            <label
              htmlFor="task-file"
              className="mb-1 block text-sm font-medium text-gray-700"
            >
              上传文档
            </label>
            <input
              id="task-file"
              type="file"
              accept=".docx,.pdf,.md"
              onChange={(e) => setFile(e.target.files?.[0])}
              className="block w-full text-sm text-gray-700"
            />
          </div>

          <div className="flex justify-end gap-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-md border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
            >
              取消
            </button>
            <button
              type="submit"
              disabled={isPending}
              className="rounded-md bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              创建任务
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
