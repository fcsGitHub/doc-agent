import React from "react";
import ReactMarkdown from "react-markdown";
import type { Section } from "@/lib/types";

export function SectionContent({ section, children }: { section: Section, children?: React.ReactNode }) {
  const getStatusText = (status: string) => {
    switch (status) {
      case "completed":
        return "已完成";
      case "generating":
        return "生成中";
      case "failed":
        return "失败";
      default:
        return "未开始";
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed":
        return "text-green-600 bg-green-50";
      case "generating":
        return "text-blue-600 bg-blue-50";
      case "failed":
        return "text-red-600 bg-red-50";
      default:
        return "text-gray-600 bg-gray-50";
    }
  };

  return (
    <div className="flex flex-col h-full bg-white relative">
      {/* Header */}
      <div className="flex items-center justify-between p-6 border-b shrink-0">
        <h2 className="text-xl font-bold text-gray-900">{section.title}</h2>
        <div className="flex items-center gap-3">
          <span className="text-sm text-gray-500 bg-gray-100 px-2 py-1 rounded-full">
            {section.word_count || 0} 字
          </span>
          <span
            className={`text-sm px-2 py-1 rounded-full ${getStatusColor(section.status)}`}
          >
            {getStatusText(section.status)}
          </span>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6 relative">
        {section.content ? (
          children || (
            <div className="text-gray-800 space-y-4">
              <ReactMarkdown
                components={{
                  h1: ({ node, ...props }) => (
                    <h1 className="text-2xl font-bold mt-6 mb-4" {...props} />
                  ),
                  h2: ({ node, ...props }) => (
                    <h2 className="text-xl font-bold mt-5 mb-3" {...props} />
                  ),
                  h3: ({ node, ...props }) => (
                    <h3 className="text-lg font-bold mt-4 mb-2" {...props} />
                  ),
                  p: ({ node, ...props }) => (
                    <p className="mb-4 leading-relaxed" {...props} />
                  ),
                  ul: ({ node, ...props }) => (
                    <ul className="list-disc pl-5 mb-4 space-y-1" {...props} />
                  ),
                  ol: ({ node, ...props }) => (
                    <ol className="list-decimal pl-5 mb-4 space-y-1" {...props} />
                  ),
                  li: ({ node, ...props }) => <li {...props} />,
                  strong: ({ node, ...props }) => (
                    <strong className="font-semibold" {...props} />
                  ),
                  em: ({ node, ...props }) => (
                    <em className="italic" {...props} />
                  ),
                  blockquote: ({ node, ...props }) => (
                    <blockquote
                      className="border-l-4 border-gray-200 pl-4 italic text-gray-600 mb-4"
                      {...props}
                    />
                  ),
                }}
              >
                {section.content}
              </ReactMarkdown>
            </div>
          )
        ) : (
          <div className="text-gray-400 text-center mt-10">
            {section.status === "generating" ? "内容正在生成中..." : "暂无内容"}
          </div>
        )}
      </div>
    </div>
  );
}

