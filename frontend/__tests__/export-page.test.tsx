import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import ExportPage from "@/app/tasks/[id]/export/page";
import { apiFetch } from "@/lib/api";
import { useLatestReview } from "@/lib/hooks/use-reviews";
import { useSections } from "@/lib/hooks/use-document";

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock("@/lib/api", () => ({
  apiFetch: vi.fn(),
}));

vi.mock("@/lib/hooks/use-document", () => ({
  useSections: vi.fn(),
}));

vi.mock("@/lib/hooks/use-reviews", () => ({
  useLatestReview: vi.fn(),
}));

const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

const renderWithClient = (ui: React.ReactElement) => {
  const testQueryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={testQueryClient}>{ui}</QueryClientProvider>,
  );
};

describe("ExportPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    process.env.NEXT_PUBLIC_API_URL = "http://localhost:8000";
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("shows pending checklist and keeps export disabled while loading", async () => {
    vi.mocked(apiFetch).mockReturnValue(new Promise(() => {}) as any);
    vi.mocked(useSections).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as any);
    vi.mocked(useLatestReview).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as any);

    renderWithClient(<ExportPage params={{ id: "task-123" }} />);

    expect(screen.getByText("所有章节已生成")).toBeInTheDocument();
    expect(screen.getByText("审核已通过")).toBeInTheDocument();
    expect(screen.getByText("最终审批已完成")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "导出 DOCX" })).toBeDisabled();
    expect(screen.getAllByText("✗").length).toBe(3);
  });

  it("enables export and downloads DOCX with the task filename", async () => {
    vi.mocked(apiFetch).mockResolvedValue({
      id: "task-123",
      name: "测试任务",
      doc_type: "bid_document",
      status: "completed",
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    });
    vi.mocked(useSections).mockReturnValue({
      data: [
        { id: "s1", title: "章节1", level: 1, status: "completed", word_count: 100 },
        { id: "s2", title: "章节2", level: 1, status: "approved", word_count: 80 },
      ],
      isLoading: false,
      isError: false,
    } as any);
    vi.mocked(useLatestReview).mockReturnValue({
      data: {
        overall_status: "approved",
        overall_score: 0.98,
        reviewer_results: [],
        issues: [],
        critical_count: 0,
        major_count: 0,
        minor_count: 0,
        info_count: 0,
      },
      isLoading: false,
      isError: false,
    } as any);

    const fetchSpy = vi.fn().mockResolvedValue({
      blob: vi.fn().mockResolvedValue(new Blob(["docx"])),
    });
    vi.stubGlobal("fetch", fetchSpy);

    const createObjectUrlMock = vi.fn().mockReturnValue("blob:mock-url");
    const revokeObjectUrlMock = vi.fn();
    Object.defineProperty(URL, "createObjectURL", {
      value: createObjectUrlMock,
      writable: true,
      configurable: true,
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      value: revokeObjectUrlMock,
      writable: true,
      configurable: true,
    });

    const clickSpy = vi
      .spyOn(HTMLAnchorElement.prototype, "click")
      .mockImplementation(() => undefined);

    renderWithClient(<ExportPage params={{ id: "task-123" }} />);

    await waitFor(() =>
      expect(screen.getByRole("button", { name: "导出 DOCX" })).toBeEnabled(),
    );

    fireEvent.click(screen.getByRole("button", { name: "导出 DOCX" }));

    await waitFor(() => {
      expect(fetchSpy).toHaveBeenCalledWith(
        "http://localhost:8000/api/v1/tasks/task-123/export/docx",
      );
      expect(clickSpy).toHaveBeenCalled();
    });

    expect(createObjectUrlMock).toHaveBeenCalled();
    expect(revokeObjectUrlMock).toHaveBeenCalledWith("blob:mock-url");
    clickSpy.mockRestore();
  });
});
