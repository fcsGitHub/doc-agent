import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

vi.mock("next/navigation", () => ({
  usePathname: vi.fn().mockReturnValue("/"),
  useRouter: vi.fn().mockReturnValue({ push: vi.fn() }),
}));

vi.mock("@/lib/hooks/use-tasks", () => ({
  useTasks: vi.fn(),
  useCreateTask: vi.fn(),
}));

import { TaskList } from "@/components/task/task-list";
import { useTasks, useCreateTask } from "@/lib/hooks/use-tasks";

const wrapper = ({ children }: { children: React.ReactNode }) => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
};

describe("TaskList", () => {
  beforeEach(() => {
    vi.mocked(useCreateTask).mockReturnValue({
      mutate: vi.fn(),
      isPending: false,
    } as any);
  });

  it("shows loading state", () => {
    vi.mocked(useTasks).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as any);
    render(<TaskList />, { wrapper });
    expect(screen.getByText("加载中...")).toBeInTheDocument();
  });

  it("shows empty state when no tasks", () => {
    vi.mocked(useTasks).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    } as any);
    render(<TaskList />, { wrapper });
    expect(screen.getByText(/暂无任务/)).toBeInTheDocument();
  });

  it("shows task items when data exists", () => {
    vi.mocked(useTasks).mockReturnValue({
      data: [
        {
          id: "1",
          name: "测试任务",
          doc_type: "bid_document",
          status: "created",
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z",
        },
      ],
      isLoading: false,
      isError: false,
    } as any);
    render(<TaskList />, { wrapper });
    expect(screen.getByText("测试任务")).toBeInTheDocument();
  });
});
