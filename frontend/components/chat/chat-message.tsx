import { ChatMessage } from "@/lib/api/chat";

interface Props { message: ChatMessage }

export function ChatMessageBubble({ message }: Props) {
  const isUser = message.role === "user";
  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-3`}>
      <div
        className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${
          isUser ? "bg-blue-600 text-white" : "bg-gray-100 text-gray-800"
        }`}
      >
        <p className="whitespace-pre-wrap">{message.content}</p>
        {message.action && message.action.status === "pending_confirmation" && (
          <div className="mt-2 text-xs bg-yellow-100 text-yellow-800 rounded p-2">
            待确认修改：{message.action.instruction}
          </div>
        )}
      </div>
    </div>
  );
}
