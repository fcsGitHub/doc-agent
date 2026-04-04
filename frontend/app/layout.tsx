import type { Metadata } from "next";
import "./globals.css";
import { QueryProvider } from "@/lib/query-provider";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";

export const metadata: Metadata = {
  title: "文档智能生产与审核平台",
  description: "基于 LLM 的文档智能生产与多角色审核平台",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body className="bg-gray-50 text-gray-900 font-sans">
        <QueryProvider>
          <div className="min-h-screen md:grid md:grid-cols-[240px_1fr]">
            <Sidebar />
            <div className="min-w-0">
              <Header />
              <main className="p-4 md:p-6">{children}</main>
            </div>
          </div>
        </QueryProvider>
      </body>
    </html>
  );
}
