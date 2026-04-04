import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReviewPanel } from "@/components/workbench/review-panel";
import { apiFetch } from "@/lib/api";

// Mock hooks and api
vi.mock("@/lib/api", () => ({
  apiFetch: vi.fn(),
}));

vi.mock("@/lib/hooks/use-sse", () => ({
  useSSE: vi.fn(() => ({ events: [], isConnected: false, error: null })),
}));

// Setup QueryClient
const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

describe("ReviewPanel Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderWithClient = (ui: React.ReactElement) => {
    const testQueryClient = createTestQueryClient();
    return render(
      <QueryClientProvider client={testQueryClient}>{ui}</QueryClientProvider>,
    );
  };

  it("renders pipeline progress steps", async () => {
    // Mock task API
    (apiFetch as any).mockImplementation(async (url: string) => {
      if (url.includes("/reviews/latest")) {
        return null;
      }
      return { id: "test-task", status: "extracting" };
    });

    renderWithClient(<ReviewPanel taskId="test-task" />);

    // Steps should be visible
    expect(screen.getByText("流水线进度")).toBeInTheDocument();

    // Wait for the task status to be processed
    await waitFor(() => {
      expect(screen.getByText("解析文档")).toBeInTheDocument();
      expect(screen.getByText("提取需求")).toBeInTheDocument();
    });
  });

  it("renders review summary with score and issues", async () => {
    (apiFetch as any).mockImplementation(async (url: string) => {
      if (url.includes("/reviews/latest")) {
        return {
          overall_status: "needs_revision",
          overall_score: 0.85,
          critical_count: 1,
          major_count: 2,
          minor_count: 3,
          info_count: 0,
          issues: [
            {
              id: "i1",
              severity: "critical",
              description: "Critical error",
              requires_human: true,
            },
          ],
        };
      }
      return { id: "test-task", status: "reviewing" };
    });

    renderWithClient(<ReviewPanel taskId="test-task" />);

    await waitFor(() => {
      expect(screen.getByText("审核摘要")).toBeInTheDocument();
      expect(screen.getByText("综合评分: 85/100")).toBeInTheDocument();
      expect(screen.getByText("需修订")).toBeInTheDocument();
      expect(screen.getByText("严重:1")).toBeInTheDocument();
      expect(screen.getByText("重要:2")).toBeInTheDocument();
      expect(screen.getByText("建议:3")).toBeInTheDocument();
    });

    // Expand issues
    const expandBtn = screen.getByText("展开问题列表");
    fireEvent.click(expandBtn);

    expect(screen.getByText("Critical error")).toBeInTheDocument();
  });

  it("calls run reviews API when '运行审核' button is clicked", async () => {
    (apiFetch as any).mockImplementation(async (url: string) => {
      if (url.includes("/reviews/latest")) {
        return null;
      }
      return { id: "test-task", status: "created" };
    });

    renderWithClient(<ReviewPanel taskId="test-task" />);

    const runBtn = await screen.findByRole("button", { name: "运行审核" });
    fireEvent.click(runBtn);

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        "/api/v1/tasks/test-task/reviews/run",
        expect.objectContaining({
          method: "POST",
        }),
      );
    });
  });

  it("calls approval API when '批准' button is clicked", async () => {
    (apiFetch as any).mockImplementation(async (url: string) => {
      if (url.includes("/reviews/latest")) {
        return {
          overall_status: "approved",
          overall_score: 1,
          critical_count: 0,
          major_count: 0,
          minor_count: 0,
          issues: [],
        };
      }
      return { id: "test-task", status: "awaiting_approval" };
    });

    renderWithClient(<ReviewPanel taskId="test-task" />);

    const approveBtn = await screen.findByText("批准");
    fireEvent.click(approveBtn);

    await waitFor(() => {
      expect(apiFetch).toHaveBeenCalledWith(
        "/api/v1/tasks/test-task/approval",
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ approved: true }),
        }),
      );
    });
  });
});
