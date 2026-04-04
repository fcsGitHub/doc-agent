import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import QualityDashboardPage from "@/app/tasks/[id]/quality/page";
import { useLatestReview } from "@/lib/hooks/use-reviews";

// Mock the hooks
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
    <QueryClientProvider client={testQueryClient}>{ui}</QueryClientProvider>
  );
};

describe("QualityDashboardPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders loading state", () => {
    vi.mocked(useLatestReview).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as any);

    renderWithClient(<QualityDashboardPage params={{ id: "task-1" }} />);
    expect(screen.getByText("加载中...")).toBeInTheDocument();
  });

  it("renders correct color class for high score", () => {
    vi.mocked(useLatestReview).mockReturnValue({
      data: {
        overall_status: "approved",
        overall_score: 0.85, // 85 -> green
        reviewer_results: [],
        issues: [],
        critical_count: 0,
        major_count: 1,
        minor_count: 2,
        info_count: 0,
      },
      isLoading: false,
      isError: false,
    } as any);

    renderWithClient(<QualityDashboardPage params={{ id: "task-1" }} />);
    
    // Overall score should be 85
    const scoreElement = screen.getByText("85");
    expect(scoreElement).toBeInTheDocument();
    expect(scoreElement.className).toContain("text-green-600");
  });

  it("renders correct color class for medium score", () => {
    vi.mocked(useLatestReview).mockReturnValue({
      data: {
        overall_status: "needs_revision",
        overall_score: 0.65, // 65 -> yellow
        reviewer_results: [],
        issues: [],
        critical_count: 1,
        major_count: 1,
        minor_count: 2,
        info_count: 0,
      },
      isLoading: false,
      isError: false,
    } as any);

    renderWithClient(<QualityDashboardPage params={{ id: "task-1" }} />);
    
    const scoreElement = screen.getByText("65");
    expect(scoreElement).toBeInTheDocument();
    expect(scoreElement.className).toContain("text-yellow-600");
  });

  it("renders correct color class for low score", () => {
    vi.mocked(useLatestReview).mockReturnValue({
      data: {
        overall_status: "rejected",
        overall_score: 0.45, // 45 -> red
        reviewer_results: [],
        issues: [],
        critical_count: 5,
        major_count: 2,
        minor_count: 1,
        info_count: 0,
      },
      isLoading: false,
      isError: false,
    } as any);

    renderWithClient(<QualityDashboardPage params={{ id: "task-1" }} />);
    
    const scoreElement = screen.getByText("45");
    expect(scoreElement).toBeInTheDocument();
    expect(scoreElement.className).toContain("text-red-600");
  });

  it("renders reviewer table with correct rows", () => {
    vi.mocked(useLatestReview).mockReturnValue({
      data: {
        overall_status: "needs_revision",
        overall_score: 0.75,
        reviewer_results: [
          {
            reviewer_name: "Alice",
            status: "pass",
            score: 0.9,
            issues: [],
          },
          {
            reviewer_name: "Bob",
            status: "fail",
            score: 0.5,
            issues: [],
          },
        ],
        issues: [],
        critical_count: 1,
        major_count: 0,
        minor_count: 2,
        info_count: 0,
      },
      isLoading: false,
      isError: false,
    } as any);

    renderWithClient(<QualityDashboardPage params={{ id: "task-1" }} />);
    
    // Check table headers
    expect(screen.getByText("审核员")).toBeInTheDocument();
    
    // Check rows are rendered
    expect(screen.getByText("Alice")).toBeInTheDocument();
    expect(screen.getByText("Bob")).toBeInTheDocument();
    
    // Check statuses
    expect(screen.getByText("通过")).toBeInTheDocument();
    expect(screen.getByText("不通过")).toBeInTheDocument();
    
    // Check scores
    expect(screen.getByText("90")).toBeInTheDocument();
    expect(screen.getByText("50")).toBeInTheDocument();

    // Check rounds logic
    // length is 2, so it should be round 2 text
    expect(screen.getByText("第1轮: 5问题 → 第2轮: 3问题")).toBeInTheDocument();
  });
});
