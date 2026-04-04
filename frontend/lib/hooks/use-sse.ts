"use client";

import { useEffect, useRef, useState } from "react";
import type { SSEEvent } from "@/lib/types";

type UseSSEReturn = {
  events: SSEEvent[];
  isConnected: boolean;
  error: string | null;
};

export function useSSE(taskId: string): UseSSEReturn {
  const [events, setEvents] = useState<SSEEvent[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!taskId) {
      setIsConnected(false);
      setError("缺少任务 ID");
      return;
    }

    let cancelled = false;

    const clearReconnectTimer = () => {
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
    };

    const disconnect = () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };

    const connect = () => {
      if (cancelled) return;

      const source = new EventSource(`/api/v1/tasks/${taskId}/progress`);
      eventSourceRef.current = source;

      source.onopen = () => {
        if (cancelled) return;
        setIsConnected(true);
        setError(null);
      };

      source.onmessage = (message) => {
        if (cancelled) return;
        let parsedData: unknown = message.data;

        try {
          parsedData = JSON.parse(message.data);
        } catch {
          parsedData = message.data;
        }

        setEvents((prev) => [
          ...prev,
          {
            event: message.type || "message",
            data: parsedData,
            timestamp: new Date().toISOString(),
          },
        ]);
      };

      source.onerror = () => {
        if (cancelled) return;

        setIsConnected(false);
        setError("SSE 连接异常，正在重连...");
        disconnect();
        clearReconnectTimer();
        reconnectTimerRef.current = setTimeout(connect, 3000);
      };
    };

    connect();

    return () => {
      cancelled = true;
      clearReconnectTimer();
      disconnect();
      setIsConnected(false);
    };
  }, [taskId]);

  return { events, isConnected, error };
}
