import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";

export interface SectionVersion {
  id: string;
  section_id: string;
  version_number: number;
  content: string;
  change_source: "generated" | "revised" | "manual"; // based on the instruction generating/revising/manual (生成/修订/手动)
  created_at: string;
}

export interface DiffLine {
  type: "add" | "delete" | "context";
  content: string;
  line_number: number;
}

export interface DiffHunk {
  lines: DiffLine[];
}

export interface DiffResult {
  version_a_id: string;
  version_b_id: string;
  hunks: DiffHunk[];
}

export function useVersions(sectionId: string | null) {
  return useQuery<SectionVersion[]>({
    queryKey: ["versions", sectionId],
    queryFn: async () => {
      const res = await apiFetch<{ versions: SectionVersion[] }>(
        `/api/v1/sections/${sectionId}/versions`,
      );
      return res.versions;
    },
    enabled: !!sectionId,
  });
}

export function useDiff(versionAId: string | null, versionBId: string | null) {
  return useQuery<DiffResult>({
    queryKey: ["diff", versionAId, versionBId],
    queryFn: async () => {
      return apiFetch<DiffResult>(
        `/api/v1/versions/diff?a=${versionAId}&b=${versionBId}`,
      );
    },
    enabled: !!versionAId && !!versionBId,
  });
}

export function useRollback(sectionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (versionId: string) => {
      return apiFetch<SectionVersion>(
        `/api/v1/sections/${sectionId}/rollback`,
        {
          method: "POST",
          body: JSON.stringify({ version_id: versionId }),
        },
      );
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["versions", sectionId] });
      // Invalidate section content as well
      queryClient.invalidateQueries({ queryKey: ["section"] });
    },
  });
}
