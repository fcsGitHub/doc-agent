import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";
import WorkbenchPage from "@/app/tasks/[id]/page";

vi.mock("@/lib/api", () => ({
  apiFetch: vi.fn(),
}));

const mockApiFetch = vi.mocked(apiFetch);

const wrapper = ({ children }: { children: React.ReactNode }) => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
};

describe("Workbench Left Panel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const mockTask = {
    id: "task-1",
    name: "测试文档任务",
    doc_type: "test",
    status: "created",
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
  };

  const mockSections = {
    sections: [
      {
        id: "sec-1",
        title: "第一章",
        level: 1,
        status: "completed",
        word_count: 100,
      },
      {
        id: "sec-2",
        title: "1.1 小节",
        level: 2,
        status: "generating",
        word_count: 50,
      },
      {
        id: "sec-3",
        title: "1.2 小节",
        level: 2,
        status: "failed",
        word_count: 0,
      },
    ],
  };

  it("renders 3-panel layout and top bar", async () => {
    mockApiFetch.mockImplementation(async (url) => {
      if (url === "/api/v1/tasks/task-1") return mockTask;
      if (url === "/api/v1/tasks/task-1/sections") return mockSections;
      return null;
    });

    render(<WorkbenchPage params={{ id: "task-1" }} />, { wrapper });

    expect(screen.getByText("加载中...")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("工作台 — 测试文档任务")).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(screen.getByText("大纲结构")).toBeInTheDocument();
    });

    expect(screen.getByText("选择左侧章节查看内容")).toBeInTheDocument();
    expect(screen.getByText("审核与进度")).toBeInTheDocument();
  });

  it("shows start button when status=created and calls mutation on click", async () => {
    mockApiFetch.mockImplementation(async (url) => {
      if (url === "/api/v1/tasks/task-1") return mockTask;
      if (url === "/api/v1/tasks/task-1/sections") return mockSections;
      if (url === "/api/v1/tasks/task-1/start") return {};
      return null;
    });

    render(<WorkbenchPage params={{ id: "task-1" }} />, { wrapper });

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: "开始处理" }),
      ).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "开始处理" }));

    await waitFor(() => {
      expect(mockApiFetch).toHaveBeenCalledWith("/api/v1/tasks/task-1/start", {
        method: "POST",
      });
    });
  });

  it("hides start button when status is not created", async () => {
    mockApiFetch.mockImplementation(async (url) => {
      if (url === "/api/v1/tasks/task-1")
        return { ...mockTask, status: "parsing" };
      if (url === "/api/v1/tasks/task-1/sections") return mockSections;
      return null;
    });

    render(<WorkbenchPage params={{ id: "task-1" }} />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText("工作台 — 测试文档任务")).toBeInTheDocument();
    });

    expect(
      screen.queryByRole("button", { name: "开始处理" }),
    ).not.toBeInTheDocument();
  });

  it("shows approve outline button when status=awaiting_outline_approval and calls mutation", async () => {
    mockApiFetch.mockImplementation(async (url) => {
      if (url === "/api/v1/tasks/task-1")
        return { ...mockTask, status: "awaiting_outline_approval" };
      if (url === "/api/v1/tasks/task-1/sections") return mockSections;
      if (url === "/api/v1/tasks/task-1/approve-outline") return {};
      return null;
    });

    render(<WorkbenchPage params={{ id: "task-1" }} />, { wrapper });

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: "审批大纲" }),
      ).toBeInTheDocument();
    });

    fireEvent.click(screen.getByRole("button", { name: "审批大纲" }));

    await waitFor(() => {
      expect(mockApiFetch).toHaveBeenCalledWith(
        "/api/v1/tasks/task-1/approve-outline",
        {
          method: "POST",
          body: JSON.stringify({ approved: true }),
        },
      );
    });
  });

  it("renders section list with correct status icons", async () => {
    mockApiFetch.mockImplementation(async (url) => {
      if (url === "/api/v1/tasks/task-1") return mockTask;
      if (url === "/api/v1/tasks/task-1/sections") return mockSections;
      return null;
    });

    render(<WorkbenchPage params={{ id: "task-1" }} />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText("第一章")).toBeInTheDocument();
    });

    expect(screen.getByText("1.1 小节")).toBeInTheDocument();
    expect(screen.getByText("1.2 小节")).toBeInTheDocument();

    // Verify icons (✓ for completed, ⟳ for generating, ✗ for failed)
    expect(screen.getByText("✓")).toBeInTheDocument();
    expect(screen.getByText("⟳")).toBeInTheDocument();
    expect(screen.getByText("✗")).toBeInTheDocument();
  });
});
