"use client";

import { useState } from "react";
import { useLLMConfigs, useCreateLLMConfig } from "@/lib/hooks/use-llm-config";
import { LLMConfigCard } from "@/components/settings/llm-config-card";
import { LLMConfigForm } from "@/components/settings/llm-config-form";

export default function SettingsPage() {
  const [showForm, setShowForm] = useState(false);
  const { data: configs, isLoading } = useLLMConfigs();
  const createConfig = useCreateLLMConfig();

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-800">LLM 配置</h1>
        <button
          onClick={() => setShowForm(true)}
          className="bg-blue-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-blue-700"
        >
          + 新增配置
        </button>
      </div>

      {showForm && (
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <h2 className="font-semibold text-gray-700 mb-3">新增 LLM 配置</h2>
          <LLMConfigForm
            onSubmit={(data) => {
              createConfig.mutate(data, { onSuccess: () => setShowForm(false) });
            }}
            onCancel={() => setShowForm(false)}
            isLoading={createConfig.isPending}
          />
        </div>
      )}

      {isLoading && <p className="text-gray-500 text-sm">加载中...</p>}

      {configs && configs.length === 0 && !showForm && (
        <p className="text-gray-500 text-sm">暂无配置，点击「新增配置」添加。</p>
      )}

      <div className="space-y-3">
        {configs?.map((c) => <LLMConfigCard key={c.id} config={c} />)}
      </div>
    </div>
  );
}
