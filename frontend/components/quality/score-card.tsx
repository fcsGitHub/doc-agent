import React from "react";

interface ScoreCardProps {
  title: string;
  value: React.ReactNode;
  valueClass?: string;
  children?: React.ReactNode;
}

export function ScoreCard({ title, value, valueClass = "text-gray-900", children }: ScoreCardProps) {
  return (
    <div className="bg-white rounded-lg shadow border p-5 flex flex-col">
      <h3 className="text-sm font-medium text-gray-500 mb-2">{title}</h3>
      <div className={`text-3xl font-bold ${valueClass}`}>{value}</div>
      {children && <div className="mt-4">{children}</div>}
    </div>
  );
}
