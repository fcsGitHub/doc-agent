import { render } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

vi.mock("next/navigation", () => ({
  usePathname: vi.fn().mockReturnValue("/"),
  useRouter: vi.fn().mockReturnValue({ push: vi.fn() }),
}));

vi.mock("@/lib/hooks/use-tasks", () => ({
  useTasks: vi
    .fn()
    .mockReturnValue({ data: [], isLoading: false, isError: false }),
  useCreateTask: vi.fn().mockReturnValue({ mutate: vi.fn(), isPending: false }),
}));

import Page from "@/app/page";

describe("Home Page", () => {
  it("renders without crashing", () => {
    const qc = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const { container } = render(
      <QueryClientProvider client={qc}>
        <Page />
      </QueryClientProvider>,
    );
    expect(container).toBeTruthy();
  });
});
