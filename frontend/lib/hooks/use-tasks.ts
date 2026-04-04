import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { Task } from "@/lib/types";

export function useTasks() {
  return useQuery<Task[]>({
    queryKey: ["tasks"],
    queryFn: async () => {
      const res = await apiFetch<{ tasks: Task[] }>("/api/v1/tasks");
      return res.tasks;
    },
  });
}

export function useCreateTask() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      name,
      doc_type,
      file,
    }: {
      name: string;
      doc_type: string;
      file?: File;
    }) => {
      const task = await apiFetch<Task>("/api/v1/tasks", {
        method: "POST",
        body: JSON.stringify({ name, doc_type }),
      });
      if (file) {
        const fd = new FormData();
        fd.append("file", file);
        const API_BASE =
          process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
        await fetch(`${API_BASE}/api/v1/tasks/${task.id}/documents/upload`, {
          method: "POST",
          body: fd,
        });
      }
      return task;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
  });
}
