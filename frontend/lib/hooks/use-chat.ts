import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, useCallback } from "react";
import { chatApi, ChatMessage } from "@/lib/api/chat";

export function useChatSessions(taskId: string) {
  return useQuery({
    queryKey: ["chat-sessions", taskId],
    queryFn: () => chatApi.listSessions(taskId),
  });
}

export function useChatMessages(sessionId: string | null) {
  return useQuery({
    queryKey: ["chat-messages", sessionId],
    queryFn: () => chatApi.listMessages(sessionId!),
    enabled: !!sessionId,
  });
}

export function useCreateChatSession(taskId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ scope, sectionId }: { scope: "task" | "section"; sectionId?: string }) =>
      chatApi.createSession(taskId, scope, sectionId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["chat-sessions", taskId] }),
  });
}

export function useSendMessage(sessionId: string, taskId: string) {
  const qc = useQueryClient();
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingReply, setStreamingReply] = useState("");

  const send = useCallback(async (content: string) => {
    setIsStreaming(true);
    setStreamingReply("");
    try {
      await chatApi.sendMessage(
        sessionId,
        content,
        (chunk) => {
          if ("reply" in chunk) setStreamingReply(chunk.reply);
        },
        () => {
          setIsStreaming(false);
          setStreamingReply("");
          qc.invalidateQueries({ queryKey: ["chat-messages", sessionId] });
        },
      );
    } catch {
      setIsStreaming(false);
    }
  }, [sessionId, qc]);

  return { send, isStreaming, streamingReply };
}
