import { apiFetch, API_BASE } from "@/lib/api";

export interface LLMConfig {
  id: string;
  name: string;
  api_key_masked: string;
  api_base: string;
  default_model: string;
  review_model: string;
  embed_model: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface LLMConfigCreate {
  name: string;
  api_key?: string;
  api_base?: string;
  default_model?: string;
  review_model?: string;
  embed_model?: string;
}

export interface LLMConfigUpdate {
  name?: string;
  api_key?: string;
  api_base?: string;
  default_model?: string;
  review_model?: string;
  embed_model?: string;
}

export const settingsApi = {
  listConfigs: () => apiFetch<LLMConfig[]>("/api/v1/settings/llm"),

  createConfig: (data: LLMConfigCreate) =>
    apiFetch<LLMConfig>("/api/v1/settings/llm", {
      method: "POST",
      body: JSON.stringify(data),
    }),

  updateConfig: (id: string, data: LLMConfigUpdate) =>
    apiFetch<LLMConfig>(`/api/v1/settings/llm/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    }),

  deleteConfig: (id: string) =>
    fetch(`${API_BASE}/api/v1/settings/llm/${id}`, { method: "DELETE" }),

  activateConfig: (id: string) =>
    apiFetch<LLMConfig>(`/api/v1/settings/llm/${id}/activate`, {
      method: "POST",
    }),
};
