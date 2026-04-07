"use client";

import { useState, useRef, useEffect } from "react";
import {
  useChatSessions,
  useChatMessages,
  useCreateChatSession,
  useSendMessage,
} from "@/lib/hooks/use-chat";
import { ChatMessageBubble } from "./chat-message";

interface Props { taskId: string }

export function ChatSidebar({ taskId }: Props) {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  const { data: sessions } = useChatSessions(taskId);
  const createSession = useCreateChatSession(taskId);
  const activeSession = sessions?.[0] ?? null;
  const { data: messages } = useChatMessages(activeSession?.id ?? null);
  const { send, isStreaming, streamingReply } = useSendMessage(
    activeSession?.id ?? "",
    taskId,
  );

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingReply]);

  const ensureSession = async () => {
    if (!activeSession) {
      await createSession.mutateAsync({ scope: "task" });
    }
  };

  const handleSend = async () => {
    if (!input.trim() || isStreaming) return;
    await ensureSession();
    const msg = input;
    setInput("");
    await send(msg);
  };

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="fixed right-4 bottom-4 z-40 bg-blue-600 text-white rounded-full w-12 h-12 flex items-center justify-center shadow-lg hover:bg-blue-700 text-xl"
        title="打开 AI 对话"
      >
        💬
      </button>
    );
  }

  return (
    <div className="fixed right-0 top-0 bottom-0 z-40 w-80 bg-white border-l border-gray-200 flex flex-col shadow-xl">
      <div className="flex items-center justify-between px-4 py-3 border-b">
        <h2 className="font-semibold text-gray-800 text-sm">AI 助手</h2>
        <button onClick={() => setOpen(false)} className="text-gray-400 hover:text-gray-600">
          ✕
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {messages?.map((m) => <ChatMessageBubble key={m.id} message={m} />)}
        {isStreaming && streamingReply && (
          <div className="flex justify-start mb-3">
            <div className="max-w-[80%] rounded-lg px-3 py-2 text-sm bg-gray-100 text-gray-800">
              <p className="whitespace-pre-wrap">{streamingReply}</p>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="border-t p-3 flex gap-2">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSend();
            }
          }}
          placeholder="输入消息（Enter 发送）"
          rows={2}
          className="flex-1 resize-none rounded border border-gray-300 px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500"
          disabled={isStreaming}
        />
        <button
          onClick={handleSend}
          disabled={isStreaming || !input.trim()}
          className="bg-blue-600 text-white px-3 rounded text-sm hover:bg-blue-700 disabled:opacity-50"
        >
          发送
        </button>
      </div>
    </div>
  );
}
