import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ContentPanel } from "@/components/workbench/content-panel";
import { SectionContent } from "@/components/workbench/section-content";
import { GenerationProgress } from "@/components/workbench/generation-progress";
import * as useDocumentHooks from "@/lib/hooks/use-document";
import * as useReviewsHooks from "@/lib/hooks/use-reviews";

// Mock the hook modules
vi.mock("@/lib/hooks/use-document", () => ({
  useSection: vi.fn(),
}));

vi.mock("@/lib/hooks/use-reviews", () => ({
  useLatestReview: vi.fn(),
}));

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

const renderWithQueryClient = (ui: React.ReactElement) => {
  return render(
    <QueryClientProvider client={queryClient}>{ui}</QueryClientProvider>,
  );
};

describe("ContentPanel Component", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useReviewsHooks.useLatestReview).mockReturnValue({
      data: { issues: [] },
      isLoading: false,
    } as any);
  });

  it("should render placeholder when sectionId is null", () => {
    vi.mocked(useDocumentHooks.useSection).mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: false,
    } as any);

    renderWithQueryClient(<ContentPanel taskId="task-123" sectionId={null} />);

    expect(screen.getByText("选择左侧章节查看内容")).toBeInTheDocument();
  });

  it("should render loading state", () => {
    vi.mocked(useDocumentHooks.useSection).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as any);

    renderWithQueryClient(
      <ContentPanel taskId="task-123" sectionId="sec-456" />,
    );

    expect(screen.getByText("加载中...")).toBeInTheDocument();
  });

  it("should render error state", () => {
    vi.mocked(useDocumentHooks.useSection).mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
    } as any);

    renderWithQueryClient(
      <ContentPanel taskId="task-123" sectionId="sec-456" />,
    );

    expect(screen.getByText("加载章节失败")).toBeInTheDocument();
  });

  it("should render section content and generation progress when data is ready", () => {
    vi.mocked(useDocumentHooks.useSection).mockReturnValue({
      data: {
        id: "sec-456",
        title: "测试章节",
        level: 1,
        status: "generating",
        word_count: 100,
        content: "# 这是一个测试标题\n\n测试章节内容。",
      },
      isLoading: false,
      isError: false,
    } as any);

    renderWithQueryClient(
      <ContentPanel taskId="task-123" sectionId="sec-456" />,
    );

    expect(screen.getByText("测试章节")).toBeInTheDocument();
    expect(screen.getByText("100 字")).toBeInTheDocument();
    expect(screen.getByText("生成中")).toBeInTheDocument();
    expect(screen.getByTestId("generation-progress")).toBeInTheDocument();
    expect(screen.getByText("这是一个测试标题")).toBeInTheDocument();
    expect(screen.getByText("这是一个测试标题").tagName).toBe("H1");
    expect(screen.getByText("测试章节内容。")).toBeInTheDocument();
  });
});

describe("GenerationProgress Component", () => {
  it("should show progress bar when status is generating", () => {
    render(<GenerationProgress status="generating" />);
    expect(screen.getByTestId("generation-progress")).toBeInTheDocument();
  });

  it("should not show progress bar when status is not generating", () => {
    const { container } = render(<GenerationProgress status="completed" />);
    expect(container.firstChild).toBeNull();
  });
});

describe("SectionContent Component", () => {
  it("should render status texts correctly", () => {
    const { rerender } = render(
      <SectionContent
        section={{
          id: "1",
          title: "Test",
          level: 1,
          status: "completed",
          word_count: 0,
        }}
      />,
    );
    expect(screen.getByText("已完成")).toBeInTheDocument();

    rerender(
      <SectionContent
        section={{
          id: "1",
          title: "Test",
          level: 1,
          status: "failed",
          word_count: 0,
        }}
      />,
    );
    expect(screen.getByText("失败")).toBeInTheDocument();

    rerender(
      <SectionContent
        section={{
          id: "1",
          title: "Test",
          level: 1,
          status: "pending",
          word_count: 0,
        }}
      />,
    );
    expect(screen.getByText("未开始")).toBeInTheDocument();
  });

  it("should show null placeholder if content is empty and not generating", () => {
    render(
      <SectionContent
        section={{
          id: "1",
          title: "Test",
          level: 1,
          status: "pending",
          word_count: 0,
        }}
      />,
    );
    expect(screen.getByText("暂无内容")).toBeInTheDocument();
  });

  it("should show generating placeholder if content is empty and generating", () => {
    render(
      <SectionContent
        section={{
          id: "1",
          title: "Test",
          level: 1,
          status: "generating",
          word_count: 0,
        }}
      />,
    );
    expect(screen.getByText("内容正在生成中...")).toBeInTheDocument();
  });
});

