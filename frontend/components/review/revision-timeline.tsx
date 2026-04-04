"use client";

interface RevisionRound {
  id: string;
  round_number: number;
  created_at: string;
  status: "approved" | "needs_revision" | "rejected";
  issue_count: number;
}

interface RevisionTimelineProps {
  rounds: RevisionRound[];
  currentRoundId?: string;
  onRoundSelect?: (id: string) => void;
}

export function RevisionTimeline({
  rounds,
  currentRoundId,
  onRoundSelect,
}: RevisionTimelineProps) {
  const statusColors = {
    approved: "bg-green-500",
    needs_revision: "bg-yellow-500",
    rejected: "bg-red-500",
  };

  const statusLabels = {
    approved: "通过",
    needs_revision: "需要修改",
    rejected: "已拒绝",
  };

  if (!rounds || rounds.length === 0) {
    return (
      <div className="text-gray-500 text-sm text-center py-4">暂无审核历史</div>
    );
  }

  // Sort descending by round number
  const sortedRounds = [...rounds].sort(
    (a, b) => b.round_number - a.round_number,
  );

  return (
    <div className="relative pl-3">
      {/* Vertical line */}
      <div className="absolute left-[19px] top-4 bottom-4 w-0.5 bg-gray-200" />

      <div className="space-y-6">
        {sortedRounds.map((round, index) => {
          const isCurrent = currentRoundId
            ? round.id === currentRoundId
            : index === 0;

          return (
            <div
              key={round.id}
              className={`relative flex items-start group ${onRoundSelect ? "cursor-pointer" : ""}`}
              onClick={() => onRoundSelect?.(round.id)}
            >
              {/* Timeline dot */}
              <div
                className={`z-10 flex-shrink-0 w-4 h-4 mt-1.5 rounded-full border-2 border-white shadow-sm ${
                  statusColors[round.status]
                } ${isCurrent ? "ring-2 ring-blue-400 ring-offset-1" : ""}`}
              />

              {/* Content card */}
              <div
                className={`ml-4 flex-1 p-3 rounded-lg border transition-all ${
                  isCurrent
                    ? "bg-blue-50 border-blue-200 shadow-sm"
                    : "bg-white border-gray-100 group-hover:border-gray-300"
                }`}
              >
                <div className="flex justify-between items-center mb-1">
                  <span className="font-medium text-sm text-gray-900">
                    第 {round.round_number} 轮审核
                  </span>
                  <span className="text-xs text-gray-500">
                    {new Date(round.created_at).toLocaleDateString("zh-CN", {
                      month: "short",
                      day: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                </div>

                <div className="flex justify-between items-center text-xs mt-2">
                  <span
                    className={`font-medium ${
                      round.status === "approved"
                        ? "text-green-700"
                        : round.status === "rejected"
                          ? "text-red-700"
                          : "text-yellow-700"
                    }`}
                  >
                    {statusLabels[round.status]}
                  </span>

                  <span className="text-gray-600">
                    {round.issue_count} 个问题
                  </span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
