"use client";

import { useState } from "react";
import { LLMConfig } from "@/lib/api/settings";
import { useActivateLLMConfig, useDeleteLLMConfig } from "@/lib/hooks/use-llm-config";

interface Props {
  config: LLMConfig;
}

export function LLMConfigCard({ config }: Props) {
  const [showKey, setShowKey] = useState(false);
  const activate = useActivateLLMConfig();
  const remove = useDeleteLLMConfig();

  return (
    <div className={`rounded-lg border p-4 ${config.is_active ? "border-blue-500 bg-blue-50" : "border-gray-200 bg-white"}`}>
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <h3 className="font-semibold text-gray-800">{config.name}</h3>
          {config.is_active && (
            <span className="text-xs bg-blue-600 text-white px-2 py-0.5 rounded-full">当前使用</span>
          )}
        </div>
        <div className="flex gap-2">
          {!config.is_active && (
            <button
              onClick={() => activate.mutate(config.id)}
              disabled={activate.isPending}
              className="text-sm bg-blue-600 text-white px-3 py-1 rounded hover:bg-blue-700 disabled:opacity-50"
            >
              激活
            </button>
          )}
          <button
            onClick={() => remove.mutate(config.id)}
            disabled={remove.isPending}
            className="text-sm border border-red-300 text-red-600 px-3 py-1 rounded hover:bg-red-50 disabled:opacity-50"
          >
            删除
          </button>
        </div>
      </div>
      <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
        <dt className="text-gray-500">API Base</dt>
        <dd className="text-gray-800 truncate">{config.api_base}</dd>
        <dt className="text-gray-500">生成模型</dt>
        <dd className="text-gray-800">{config.default_model}</dd>
        <dt className="text-gray-500">审阅模型</dt>
        <dd className="text-gray-800">{config.review_model}</dd>
        <dt className="text-gray-500">嵌入模型</dt>
        <dd className="text-gray-800">{config.embed_model}</dd>
        <dt className="text-gray-500">API Key</dt>
        <dd className="text-gray-800">
          {showKey ? config.api_key_masked : "••••••••"}
          <button
            onClick={() => setShowKey((v) => !v)}
            className="ml-2 text-xs text-blue-600 hover:underline"
          >
            {showKey ? "隐藏" : "显示"}
          </button>
        </dd>
      </dl>
    </div>
  );
}
