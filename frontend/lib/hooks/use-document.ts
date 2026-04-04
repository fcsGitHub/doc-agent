import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { Task, Section } from "@/lib/types";

export function useTask(id: string) {
  return useQuery<Task>({
    queryKey: ["task", id],
    queryFn: async () => apiFetch<Task>(`/api/v1/tasks/${id}`),
    enabled: !!id,
  });
}

export function useSection(taskId: string, sectionId: string | null) {
  return useQuery<Section>({
    queryKey: ["section", taskId, sectionId],
    queryFn: async () =>
      apiFetch<Section>(`/api/v1/tasks/${taskId}/sections/${sectionId}`),
    enabled: !!taskId && !!sectionId,
  });
}

export function useSections(taskId: string) {
  return useQuery<Section[]>({
    queryKey: ["sections", taskId],
    queryFn: async () => {
      const res = await apiFetch<{ sections: Section[] }>(
        `/api/v1/tasks/${taskId}/sections`,
      );
      return res.sections;
    },
    enabled: !!taskId,
  });
}

export function useStartTask(taskId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      return apiFetch(`/api/v1/tasks/${taskId}/start`, {
        method: "POST",
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["task", taskId] });
    },
  });
}

export function useApproveOutline(taskId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      return apiFetch(`/api/v1/tasks/${taskId}/approve-outline`, {
        method: "POST",
        body: JSON.stringify({ approved: true }),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["task", taskId] });
    },
  });
}
