"use client";

import Link from "next/link";
import { useState } from "react";
import { useTasks } from "@/lib/hooks/use-tasks";
import type { TaskStatus } from "@/lib/types";
import { CreateTaskDialog } from "@/components/task/create-task-dialog";

function getStatusMeta(status: TaskStatus): {
  text: string;
  className: string;
} {
  if (status === "created") {
    return { text: "已创建", className: "bg-gray-100 text-gray-700" };
  }

  if (["parsing", "extracting", "planning", "generating"].includes(status)) {
    return { text: "进行中", className: "bg-blue-100 text-blue-700" };
  }

  if (status === "reviewing") {
    return { text: "审核中", className: "bg-yellow-100 text-yellow-700" };
  }

  if (["awaiting_outline_approval", "awaiting_approval"].includes(status)) {
    return { text: "待审批", className: "bg-orange-100 text-orange-700" };
  }

  if (["approved", "completed"].includes(status)) {
    return { text: "已完成", className: "bg-green-100 text-green-700" };
  }

  if (status === "failed") {
    return { text: "失败", className: "bg-red-100 text-red-700" };
  }

  return { text: status, className: "bg-gray-100 text-gray-700" };
}

export function TaskList() {
  const [open, setOpen] = useState(false);
  const { data, isLoading, isError } = useTasks();

  if (isLoading) {
    return <div className="p-6 text-gray-700">加载中...</div>;
  }

  if (isError) {
    return <div className="p-6 text-red-600">加载失败，请重试</div>;
  }

  const tasks = data ?? [];

  return (
    <section className="space-y-4 p-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">任务列表</h1>
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          新建任务
        </button>
      </div>

      {tasks.length === 0 ? (
        <div className="rounded-lg border border-dashed border-gray-300 bg-white p-8 text-center">
          <p className="text-gray-600">暂无任务，点击'新建任务'开始</p>
          <button
            type="button"
            onClick={() => setOpen(true)}
            className="mt-4 rounded-md border border-gray-300 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50"
          >
            新建任务
          </button>
        </div>
      ) : (
        <div className="overflow-hidden rounded-lg border border-gray-200 bg-white">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  任务名称
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  文档类型
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  状态
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                  创建时间
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 bg-white">
              {tasks.map((task) => {
                const statusMeta = getStatusMeta(task.status);

                return (
                  <tr key={task.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm text-gray-900">
                      <Link href={`/tasks/${task.id}`} className="block w-full">
                        {task.name}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">
                      <Link href={`/tasks/${task.id}`} className="block w-full">
                        {task.doc_type}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-sm">
                      <Link href={`/tasks/${task.id}`} className="block w-full">
                        <span
                          className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${statusMeta.className}`}
                        >
                          {statusMeta.text}
                        </span>
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600">
                      <Link href={`/tasks/${task.id}`} className="block w-full">
                        {new Date(task.created_at).toLocaleString("zh-CN")}
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <CreateTaskDialog open={open} onClose={() => setOpen(false)} />
    </section>
  );
}
