import path from "node:path";
import { expect, test } from "@playwright/test";

const BACKEND_URL = "http://localhost:8000";
const TASK_NAME = "E2E测试投标书";

async function waitForTaskStatus(
  request: Parameters<Parameters<typeof test>[1]>[0]["request"],
  taskId: string,
  targetStatuses: string[],
  timeoutMs = 90000,
) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const res = await request.get(`${BACKEND_URL}/api/v1/tasks/${taskId}`);
    if (res.ok()) {
      const task = await res.json();
      if (targetStatuses.includes(task.status)) {
        return task;
      }
    }
    await new Promise((resolve) => setTimeout(resolve, 1500));
  }
  throw new Error(
    `Task ${taskId} did not reach one of statuses: ${targetStatuses.join(", ")}`,
  );
}

async function waitForCompletedSections(
  request: Parameters<Parameters<typeof test>[1]>[0]["request"],
  taskId: string,
  timeoutMs = 90000,
) {
  const start = Date.now();
  while (Date.now() - start < timeoutMs) {
    const res = await request.get(`${BACKEND_URL}/api/v1/tasks/${taskId}/sections`);
    if (res.ok()) {
      const sections = (await res.json()) as Array<{ status: string }>;
      if (sections.length > 0 && sections.every((s) => s.status === "completed")) {
        return sections;
      }
    }
    await new Promise((resolve) => setTimeout(resolve, 1500));
  }
  throw new Error(`Sections for task ${taskId} were not fully generated in time`);
}

test("T51 smoke test: happy path across key pages", async ({ page, request }) => {
  if (process.env.LITELLM_MOCK !== "true") {
    throw new Error("LITELLM_MOCK must be true for deterministic smoke testing");
  }

  const fixturePath = path.resolve(__dirname, "fixtures", "test-doc.docx");

  await test.step("1) Navigate home and verify demo task exists", async () => {
    await page.goto("/");
    await expect(page.getByRole("button", { name: "新建任务" })).toBeVisible();
    await expect(page.getByText("示例投标书")).toBeVisible();
  });

  await test.step("2) Open create task dialog", async () => {
    await page.getByRole("button", { name: "新建任务" }).click();
    await expect(page.getByRole("heading", { name: "新建任务" })).toBeVisible();
  });

  await test.step("3) Fill task name and doc type", async () => {
    await page.getByLabel("任务名称").fill(TASK_NAME);
    await page.getByLabel("文档类型").selectOption({ label: "投标书" });
  });

  await test.step("4) Attach DOCX fixture", async () => {
    await page.getByLabel("上传文档").setInputFiles(fixturePath);
  });

  await test.step("5) Submit and verify new task in list", async () => {
    await page.getByRole("button", { name: "创建任务" }).click();
    await expect(page.getByText(TASK_NAME)).toBeVisible({ timeout: 30000 });
  });

  let taskId = "";
  await test.step("6) Open new task row and go to workbench", async () => {
    await page.getByRole("link", { name: TASK_NAME }).first().click();
    await expect(page).toHaveURL(/\/tasks\/[^/]+$/);
    const match = page.url().match(/\/tasks\/([^/?#]+)/);
    taskId = match?.[1] ?? "";
    expect(taskId).not.toBe("");
  });

  await test.step("7) Verify start button visible", async () => {
    await expect(page.getByRole("button", { name: "开始处理" })).toBeVisible();
  });

  await test.step("8) Start processing pipeline", async () => {
    await page.getByRole("button", { name: "开始处理" }).click();
    await expect(page.getByText("流水线进度")).toBeVisible();
  });

  await test.step("9) Wait for outline/sections to appear", async () => {
    await expect(
      page.locator("div.flex-1.overflow-y-auto.p-2 ul li").first(),
    ).toBeVisible({ timeout: 90000 });
  });

  await test.step("10) Assert left panel has section items", async () => {
    const sectionItems = page.locator("div.flex-1.overflow-y-auto.p-2 ul li");
    await expect
      .poll(async () => sectionItems.count(), { timeout: 90000 })
      .toBeGreaterThan(0);
  });

  await test.step("11) Approve outline", async () => {
    const approveOutlineBtn = page.getByRole("button", { name: "审批大纲" });
    if (await approveOutlineBtn.isVisible({ timeout: 60000 }).catch(() => false)) {
      await approveOutlineBtn.click();
    }
  });

  await test.step("12) Wait for section generation complete", async () => {
    await waitForCompletedSections(request, taskId);
  });

  await test.step("13) Open one section and assert content loads", async () => {
    const firstSection = page.locator("div.flex-1.overflow-y-auto.p-2 ul li").first();
    await firstSection.click();
    await expect(page.getByRole("button", { name: /显示审核标注|隐藏审核标注/ })).toBeVisible();
    await expect(page.getByText("加载章节失败")).toHaveCount(0);
  });

  await test.step("14) Run review and wait complete", async () => {
    await page.getByRole("button", { name: "运行审核" }).click();
    await expect(page.getByText("审核摘要")).toBeVisible({ timeout: 90000 });
  });

  await test.step("15) Assert review results visible", async () => {
    await expect(page.getByText(/综合评分:\s*\d+\/100/)).toBeVisible();
  });

  await test.step("16) Go to review dashboard and assert 8 reviewer cards", async () => {
    await page.goto(`/tasks/${taskId}/reviews`);
    await expect(page.getByRole("heading", { name: "审核面板" })).toBeVisible();
    const reviewerGrid = page
      .locator("section")
      .filter({ hasText: "审核结果" })
      .first();
    await expect(reviewerGrid.locator("h3")).toHaveCount(8, { timeout: 60000 });
  });

  await test.step("17) Navigate back to workbench", async () => {
    await page.goto(`/tasks/${taskId}`);
    await expect(page.getByText("工作台")).toBeVisible();
  });

  await test.step("18) Navigate export page and verify checklist", async () => {
    const approveBtn = page.getByRole("button", { name: "批准" });
    if (await approveBtn.isVisible().catch(() => false)) {
      await approveBtn.click();
      await waitForTaskStatus(request, taskId, ["approved", "completed"], 60000);
    }

    await page.goto(`/tasks/${taskId}/export`);
    await expect(page.getByRole("heading", { name: "导出前检查" })).toBeVisible();
  });

  await test.step("19) Click export DOCX and assert download", async () => {
    const downloadPromise = page.waitForEvent("download", { timeout: 30000 });
    await page.getByRole("button", { name: "导出 DOCX" }).click();
    const download = await downloadPromise;
    expect(download.suggestedFilename().toLowerCase()).toContain(".docx");
  });

  await test.step("20) Navigate knowledge page and assert upload zone", async () => {
    await page.goto("/knowledge");
    await expect(page.getByText("点击或将文件拖拽至此处上传")).toBeVisible();
  });

  await test.step("21) Navigate quality page and assert score card", async () => {
    await page.goto(`/tasks/${taskId}/quality`);
    await expect(page.getByText("综合评分")).toBeVisible();
  });

  await test.step("22) Navigate versions page and assert version list area", async () => {
    await page.goto(`/tasks/${taskId}/versions`);
    await expect(
      page.getByText(/版本历史|暂无版本历史|任务中没有可用的章节/),
    ).toBeVisible();
  });
});
