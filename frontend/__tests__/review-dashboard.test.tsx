import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import ReviewDashboardPage from "@/app/tasks/[id]/reviews/page";
import { useLatestReview } from "@/lib/hooks/use-reviews";
import type { AggregatedReview } from "@/lib/types";

vi.mock("next/link", () => ({
  default: ({
    children,
    href,
  }: {
    children: React.ReactNode;
    href: string;
  }) => <a href={href}>{children}</a>,
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

describe("Review Dashboard Page", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderWithClient = (ui: React.ReactElement) => {
    const testQueryClient = createTestQueryClient();
    return render(
      <QueryClientProvider client={testQueryClient}>{ui}</QueryClientProvider>,
    );
  };

  const mockReview: AggregatedReview = {
    overall_status: "needs_revision",
    overall_score: 0.85,
    critical_count: 1,
    major_count: 0,
    minor_count: 1,
    info_count: 0,
    issues: [],
    reviewer_results: [
      {
        reviewer_name: "structure",
        status: "pass",
        score: 1.0,
        issues: [],
      },
      {
        reviewer_name: "compliance",
        status: "fail",
        score: 0.7,
        issues: [
          {
            id: "i1",
            severity: "critical",
            description: "Missing copyright",
            requires_human: true,
          },
          {
            id: "i2",
            severity: "minor",
            description: "Formatting issue",
            requires_human: false,
          },
        ],
      },
    ],
  };

  it("renders reviewer cards correctly", () => {
    (useLatestReview as any).mockReturnValue({
      data: mockReview,
      isLoading: false,
      isError: false,
    });

    renderWithClient(<ReviewDashboardPage params={{ id: "task-123" }} />);

    expect(screen.getByText("格式审核")).toBeInTheDocument();
    expect(screen.getAllByText("合规审核").length).toBeGreaterThan(0);
    expect(screen.getByText("返回工作台")).toBeInTheDocument();
    expect(screen.getByText("85")).toBeInTheDocument();
    expect(screen.getByText("/100")).toBeInTheDocument();
  });

  it("filters issue table by severity", () => {
    (useLatestReview as any).mockReturnValue({
      data: mockReview,
      isLoading: false,
      isError: false,
    });

    renderWithClient(<ReviewDashboardPage params={{ id: "task-123" }} />);

    // Both issues should be present initially
    expect(screen.getByText("Missing copyright")).toBeInTheDocument();
    expect(screen.getByText("Formatting issue")).toBeInTheDocument();

    // Click critical filter
    const criticalBtn = screen.getByRole("button", { name: "严重" });
    fireEvent.click(criticalBtn);

    expect(screen.getByText("Missing copyright")).toBeInTheDocument();
    expect(screen.queryByText("Formatting issue")).not.toBeInTheDocument();
  });

  it("renders revision timeline with rounds", () => {
    (useLatestReview as any).mockReturnValue({
      data: mockReview,
      isLoading: false,
      isError: false,
    });

    renderWithClient(<ReviewDashboardPage params={{ id: "task-123" }} />);

    expect(screen.getByText("审核历史")).toBeInTheDocument();
    expect(screen.getByText("第 1 轮审核")).toBeInTheDocument();
    expect(screen.getAllByText("需要修改").length).toBeGreaterThan(0);
    expect(screen.getByText("2 个问题")).toBeInTheDocument();
  });
});
