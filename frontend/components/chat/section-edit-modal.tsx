"use client";

import { useState } from "react";
import { useCreateChatSession, useChatSessions } from "@/lib/hooks/use-chat";
import { chatApi } from "@/lib/api/chat";

interface Props {
  taskId: string;
  sectionId: string;
  sectionTitle: string;
  onClose: () => void;
}

export function SectionEditModal({ taskId, sectionId, sectionTitle, onClose }: Props) {
  const [instruction, setInstruction] = useState("");
  const [result, setResult] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const createSession = useCreateChatSession(taskId);
  const { data: sessions } = useChatSessions(taskId);

  const getSectionSession = async () => {
    const existing = sessions?.find(
      (s) => s.scope === "section" && s.section_id === sectionId,
    );
    if (existing) return existing;
    return createSession.mutateAsync({ scope: "section", sectionId });
  };

  const handleSubmit = async () => {
    if (!instruction.trim() || submitting) return;
    setSubmitting(true);
    try {
      const session = await getSectionSession();
      await chatApi.sendMessage(
        session.id,
        `针对章节「${sectionTitle}」：${instruction}`,
        (chunk) => {
          if ("reply" in chunk) setResult(chunk.reply);
        },
        () => setSubmitting(false),
      );
    } catch {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-lg shadow-xl w-[480px] max-w-full p-6 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-gray-800">AI 修改章节：{sectionTitle}</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600">✕</button>
        </div>

        {!result ? (
          <>
            <textarea
              value={instruction}
              onChange={(e) => setInstruction(e.target.value)}
              placeholder="描述你希望如何修改这个章节..."
              rows={4}
              className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
            <div className="flex gap-2 justify-end">
              <button
                onClick={onClose}
                className="border border-gray-300 px-4 py-2 rounded text-sm hover:bg-gray-50"
              >
                取消
              </button>
              <button
                onClick={handleSubmit}
                disabled={!instruction.trim() || submitting}
                className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700 disabled:opacity-50"
              >
                {submitting ? "处理中..." : "提交"}
              </button>
            </div>
          </>
        ) : (
          <>
            <div className="rounded bg-gray-50 border border-gray-200 p-3 text-sm text-gray-800 whitespace-pre-wrap">
              {result}
            </div>
            <div className="flex gap-2 justify-end">
              <button
                onClick={onClose}
                className="border border-gray-300 px-4 py-2 rounded text-sm hover:bg-gray-50"
              >
                关闭
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
