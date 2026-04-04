import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  usePathname: vi.fn().mockReturnValue("/"),
}));

vi.mock("next/font/google", () => ({
  Noto_Sans_SC: vi.fn(() => ({
    variable: "--font-sans",
  })),
}));

import RootLayout from "@/app/layout";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";

describe("Layout Components", () => {
  it("sidebar renders all navigation links", () => {
    render(<Sidebar />);

    expect(screen.getByRole("link", { name: "任务列表" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "工作台" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "知识库" })).toBeInTheDocument();
  });

  it("header renders platform title", () => {
    render(<Header />);

    expect(screen.getByText("文档智能平台")).toBeInTheDocument();
  });

  it("root layout renders children", () => {
    render(
      <RootLayout>
        <div>布局内容</div>
      </RootLayout>,
    );

    expect(screen.getByText("布局内容")).toBeInTheDocument();
  });
});
