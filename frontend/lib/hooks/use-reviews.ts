import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import type { AggregatedReview } from "@/lib/types";

export function useLatestReview(taskId: string) {
  return useQuery<AggregatedReview>({
    queryKey: ["review", taskId],
    queryFn: async () => {
      return apiFetch<AggregatedReview>(
        `/api/v1/tasks/${taskId}/reviews/latest`,
      );
    },
    enabled: !!taskId,
  });
}

export function useRunReviews(taskId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      return apiFetch(`/api/v1/tasks/${taskId}/reviews/run`, {
        method: "POST",
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["review", taskId] });
    },
  });
}

export function useSubmitApproval(taskId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({ approved }: { approved: boolean }) => {
      return apiFetch(`/api/v1/tasks/${taskId}/approval`, {
        method: "POST",
        body: JSON.stringify({ approved }),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["task", taskId] });
      queryClient.invalidateQueries({ queryKey: ["review", taskId] });
    },
  });
}
