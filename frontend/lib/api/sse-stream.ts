/**
 * Parses a server-sent events (SSE) stream from a fetch Response.
 * Calls onEvent for each parsed JSON payload; stops on "[DONE]" sentinel.
 */
export async function parseSSEStream(
  res: Response,
  onEvent: (data: unknown) => void,
): Promise<void> {
  const reader = res.body!.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const lines = buf.split("\n");
    buf = lines.pop() ?? "";
    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      const payload = line.slice(6).trim();
      if (payload === "[DONE]") return;
      try { onEvent(JSON.parse(payload)); } catch { /* ignore malformed */ }
    }
  }
}
