"use client";

import { useState } from "react";
import { LLMConfigCreate } from "@/lib/api/settings";

interface Props {
  onSubmit: (data: LLMConfigCreate) => void;
  onCancel: () => void;
  isLoading?: boolean;
  initialValues?: Partial<LLMConfigCreate>;
}

export function LLMConfigForm({ onSubmit, onCancel, isLoading, initialValues }: Props) {
  const [form, setForm] = useState<LLMConfigCreate>({
    name: initialValues?.name ?? "",
    api_key: initialValues?.api_key ?? "",
    api_base: initialValues?.api_base ?? "https://api.openai.com/v1",
    default_model: initialValues?.default_model ?? "gpt-4o-mini",
    review_model: initialValues?.review_model ?? "gpt-4o",
    embed_model: initialValues?.embed_model ?? "text-embedding-3-small",
  });

  const fields: { key: keyof LLMConfigCreate; label: string; type?: string }[] = [
    { key: "name", label: "配置名称" },
    { key: "api_key", label: "API Key", type: "password" },
    { key: "api_base", label: "API Base URL" },
    { key: "default_model", label: "生成模型" },
    { key: "review_model", label: "审阅模型" },
    { key: "embed_model", label: "嵌入模型" },
  ];

  return (
    <form
      onSubmit={(e) => { e.preventDefault(); onSubmit(form); }}
      className="space-y-4"
    >
      {fields.map(({ key, label, type }) => (
        <div key={key}>
          <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
          <input
            type={type ?? "text"}
            value={form[key] ?? ""}
            onChange={(e) => setForm({ ...form, [key]: e.target.value })}
            className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            required={key === "name"}
          />
        </div>
      ))}
      <div className="flex gap-2 pt-2">
        <button
          type="submit"
          disabled={isLoading}
          className="bg-blue-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          {isLoading ? "保存中..." : "保存"}
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="border border-gray-300 px-4 py-2 rounded text-sm font-medium hover:bg-gray-50"
        >
          取消
        </button>
      </div>
    </form>
  );
}
