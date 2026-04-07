import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { settingsApi, LLMConfigCreate, LLMConfigUpdate } from "@/lib/api/settings";

export const LLM_CONFIG_KEY = ["llm-configs"] as const;

export function useLLMConfigs() {
  return useQuery({
    queryKey: LLM_CONFIG_KEY,
    queryFn: settingsApi.listConfigs,
  });
}

export function useCreateLLMConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: LLMConfigCreate) => settingsApi.createConfig(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: LLM_CONFIG_KEY }),
  });
}

export function useUpdateLLMConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: LLMConfigUpdate }) =>
      settingsApi.updateConfig(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: LLM_CONFIG_KEY }),
  });
}

export function useDeleteLLMConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => settingsApi.deleteConfig(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: LLM_CONFIG_KEY }),
  });
}

export function useActivateLLMConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => settingsApi.activateConfig(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: LLM_CONFIG_KEY }),
  });
}
