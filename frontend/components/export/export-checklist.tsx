interface ExportChecklistProps {
  sectionsGenerated: boolean;
  reviewsPassed: boolean;
  finalApprovalCompleted: boolean;
}

const ITEMS = [
  { key: "sectionsGenerated", label: "所有章节已生成" },
  { key: "reviewsPassed", label: "审核已通过" },
  { key: "finalApprovalCompleted", label: "最终审批已完成" },
] as const;

export function ExportChecklist({
  sectionsGenerated,
  reviewsPassed,
  finalApprovalCompleted,
}: ExportChecklistProps) {
  const state = {
    sectionsGenerated,
    reviewsPassed,
    finalApprovalCompleted,
  };

  return (
    <section className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
      <h2 className="mb-4 text-base font-semibold text-gray-900">导出前检查</h2>
      <ul className="space-y-3">
        {ITEMS.map((item) => {
          const checked = state[item.key];

          return (
            <li key={item.key} className="flex items-center gap-3 text-sm">
              <span
                className={`inline-flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold ${
                  checked
                    ? "bg-green-100 text-green-700"
                    : "bg-gray-100 text-gray-500"
                }`}
                aria-hidden="true"
              >
                {checked ? "✓" : "✗"}
              </span>
              <span className={checked ? "text-gray-900" : "text-gray-500"}>
                {item.label}
              </span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
