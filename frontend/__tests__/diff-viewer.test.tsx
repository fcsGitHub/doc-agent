import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

vi.mock("@/lib/hooks/use-versions", () => ({
  useDiff: vi.fn(),
}));

import { DiffViewer } from "@/components/version/diff-viewer";
import { useDiff } from "@/lib/hooks/use-versions";

const wrapper = ({ children }: { children: React.ReactNode }) => {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
};

describe("DiffViewer", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("renders '请选择两个版本进行对比' when no versions selected", () => {
    vi.mocked(useDiff).mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: false,
    } as any);
    render(<DiffViewer versionAId={null} versionBId={null} />, { wrapper });

    expect(screen.getByText("请选择两个版本进行对比")).toBeInTheDocument();
  });

  it("renders additions in green and deletions in red when diff data provided", () => {
    const diffData = {
      version_a_id: "v1",
      version_b_id: "v2",
      hunks: [
        {
          lines: [
            { type: "add", content: "Added line", line_number: 1 },
            { type: "delete", content: "Deleted line", line_number: 2 },
            { type: "context", content: "Context line", line_number: 3 },
          ],
        },
      ],
    };

    vi.mocked(useDiff).mockReturnValue({
      data: diffData,
      isLoading: false,
      isError: false,
    } as any);
    const { container } = render(
      <DiffViewer versionAId="v1" versionBId="v2" />,
      { wrapper },
    );

    const addedLine = screen.getByText("Added line");
    expect(addedLine.parentElement?.parentElement).toHaveClass(
      "bg-green-100",
      "text-green-800",
    );

    const deletedLine = screen.getByText("Deleted line");
    expect(deletedLine).toHaveClass("line-through");
    expect(deletedLine.parentElement?.parentElement).toHaveClass(
      "bg-red-100",
      "text-red-800",
    );
  });

  it("renders line numbers", () => {
    const diffData = {
      version_a_id: "v1",
      version_b_id: "v2",
      hunks: [
        {
          lines: [{ type: "context", content: "Some text", line_number: 42 }],
        },
      ],
    };

    vi.mocked(useDiff).mockReturnValue({
      data: diffData,
      isLoading: false,
      isError: false,
    } as any);
    render(<DiffViewer versionAId="v1" versionBId="v2" />, { wrapper });

    expect(screen.getByText("42")).toBeInTheDocument();
  });
});
