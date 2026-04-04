import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import KnowledgePage from "@/app/knowledge/page";
import { apiFetch } from "@/lib/api";

// Mock apiFetch as instructed
vi.mock("@/lib/api", () => ({
  apiFetch: vi.fn(),
}));

const wrapper = ({ children }: { children: React.ReactNode }) => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
};

describe("Knowledge Page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders knowledge base stats and loading states initially", () => {
    // Mock the initial fetches to return empty/loading state
    vi.mocked(apiFetch).mockImplementation((path) => {
      if (path === "/api/v1/knowledge/stats") {
        return new Promise(() => {}); // never resolves to keep it loading
      }
      if (path === "/api/v1/knowledge/documents") {
        return new Promise(() => {}); // never resolves
      }
      return Promise.resolve({});
    });

    render(<KnowledgePage />, { wrapper });
    
    expect(screen.getByText("知识库管理")).toBeInTheDocument();
    expect(screen.getByText("总文档数")).toBeInTheDocument();
    expect(screen.getByText("总分块数")).toBeInTheDocument();
    
    // Upload zone text
    expect(screen.getByText("点击或将文件拖拽至此处上传")).toBeInTheDocument();
    expect(screen.getByText("支持的格式: .pdf, .docx, .md, .txt")).toBeInTheDocument();
  });

  it("renders loaded stats and documents successfully", async () => {
    vi.mocked(apiFetch).mockImplementation(async (path) => {
      if (path === "/api/v1/knowledge/stats") {
        return { total_documents: 10, total_chunks: 50, last_updated: "2026-04-01T12:00:00Z" };
      }
      if (path === "/api/v1/knowledge/documents") {
        return {
          documents: [
            {
              id: "doc-1",
              filename: "test-doc.pdf",
              file_type: "pdf",
              chunk_count: 5,
              created_at: "2026-04-01T12:00:00Z",
            }
          ]
        };
      }
      return {};
    });

    render(<KnowledgePage />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText("10")).toBeInTheDocument(); // total docs
      expect(screen.getByText("50")).toBeInTheDocument(); // total chunks
      expect(screen.getByText("test-doc.pdf")).toBeInTheDocument(); // doc list
    });
  });

  it("allows searching and displays results", async () => {
    vi.mocked(apiFetch).mockImplementation(async (path) => {
      if (path === "/api/v1/knowledge/stats") {
        return { total_documents: 1, total_chunks: 1, last_updated: null };
      }
      if (path === "/api/v1/knowledge/documents") {
        return { documents: [] };
      }
      if (path === "/api/v1/knowledge/search") {
        return {
          results: [
            {
              content: "这是一个搜索结果片段",
              score: 0.95,
              document_name: "test-doc.pdf",
            }
          ]
        };
      }
      return {};
    });

    render(<KnowledgePage />, { wrapper });

    const searchInput = screen.getByPlaceholderText("输入搜索关键词...");
    const searchButton = screen.getByText("搜索");

    fireEvent.change(searchInput, { target: { value: "测试" } });
    fireEvent.click(searchButton);

    await waitFor(() => {
      expect(screen.getByText("这是一个搜索结果片段")).toBeInTheDocument();
      expect(screen.getByText("相关度: 0.950")).toBeInTheDocument();
    });
  });
});
