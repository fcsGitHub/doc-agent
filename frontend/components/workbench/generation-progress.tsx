import React from "react";

export function GenerationProgress({ status }: { status: string }) {
  if (status !== "generating") {
    return null;
  }

  return (
    <div
      className="w-full bg-blue-50 h-1.5 rounded overflow-hidden mt-4"
      data-testid="generation-progress"
    >
      <div className="bg-blue-500 h-full animate-pulse w-full origin-left scale-x-100 transition-transform duration-1000 ease-in-out" />
    </div>
  );
}
