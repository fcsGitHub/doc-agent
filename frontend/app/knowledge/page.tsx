"use client";

import { useKnowledgeDocs, useKnowledgeStats, useDeleteDocument } from "@/lib/hooks/use-knowledge";
import { UploadZone } from "@/components/knowledge/upload-zone";
import { SearchTest } from "@/components/knowledge/search-test";

export default function KnowledgePage() {
  const { data: stats, isLoading: statsLoading } = useKnowledgeStats();
  const { data: docs, isLoading: docsLoading } = useKnowledgeDocs();
  const { mutate: deleteDoc, isPending: isDeleting } = useDeleteDocument();

  const handleDelete = (id: string, name: string) => {
    if (confirm(`确定要删除文档 "${name}" 吗？此操作不可恢复。`)) {
      deleteDoc(id);
    }
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return "-";
    return new Date(dateString).toLocaleString("zh-CN");
  };

  return (
    <div className="mx-auto max-w-6xl p-6">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">知识库管理</h1>
        <p className="mt-1 text-sm text-gray-500">上传并管理平台知识库文档，支持全文语义搜索。</p>
      </div>

      <div className="mb-8 grid grid-cols-1 gap-6 md:grid-cols-3">
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <div className="text-sm font-medium text-gray-500">总文档数</div>
          <div className="mt-2 text-3xl font-bold text-gray-900">
            {statsLoading ? "..." : stats?.total_documents ?? 0}
          </div>
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <div className="text-sm font-medium text-gray-500">总分块数</div>
          <div className="mt-2 text-3xl font-bold text-gray-900">
            {statsLoading ? "..." : stats?.total_chunks ?? 0}
          </div>
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-6 shadow-sm">
          <div className="text-sm font-medium text-gray-500">最后更新时间</div>
          <div className="mt-2 text-lg font-bold text-gray-900">
            {statsLoading ? "..." : formatDate(stats?.last_updated ?? null)}
          </div>
        </div>
      </div>

      <div className="mb-8">
        <UploadZone />
      </div>

      <div className="mb-8 grid grid-cols-1 gap-8 lg:grid-cols-2">
        <div className="rounded-lg border border-gray-200 bg-white shadow-sm overflow-hidden">
          <div className="border-b border-gray-200 bg-gray-50 px-6 py-4">
            <h2 className="text-lg font-semibold text-gray-900">文档列表</h2>
          </div>
          
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-gray-600">
              <thead className="bg-gray-50 text-gray-700">
                <tr>
                  <th className="px-6 py-3 font-medium">文档名称</th>
                  <th className="px-6 py-3 font-medium">类型</th>
                  <th className="px-6 py-3 font-medium">块数</th>
                  <th className="px-6 py-3 font-medium">上传时间</th>
                  <th className="px-6 py-3 font-medium text-right">操作</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {docsLoading ? (
                  <tr>
                    <td colSpan={5} className="px-6 py-8 text-center text-gray-500">
                      加载中...
                    </td>
                  </tr>
                ) : !docs || docs.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-6 py-8 text-center text-gray-500">
                      暂无文档，请先上传
                    </td>
                  </tr>
                ) : (
                  docs.map((doc) => (
                    <tr key={doc.id} className="hover:bg-gray-50">
                      <td className="px-6 py-4 font-medium text-gray-900">
                        {doc.filename}
                      </td>
                      <td className="px-6 py-4">{doc.file_type.toUpperCase()}</td>
                      <td className="px-6 py-4">{doc.chunk_count}</td>
                      <td className="px-6 py-4">{formatDate(doc.created_at)}</td>
                      <td className="px-6 py-4 text-right">
                        <button
                          onClick={() => handleDelete(doc.id, doc.filename)}
                          disabled={isDeleting}
                          className="text-red-600 hover:text-red-800 disabled:opacity-50"
                        >
                          删除
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div>
          <SearchTest />
        </div>
      </div>
    </div>
  );
}
