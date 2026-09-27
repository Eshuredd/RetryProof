import type { ReactNode } from "react";

interface StatRowProps {
  label: string;
  value: ReactNode;
  highlight?: "fail" | "pass" | "neutral";
}

export function StatRow({ label, value, highlight = "neutral" }: StatRowProps) {
  const valueClass =
    highlight === "fail"
      ? "text-[#cf222e] font-semibold"
      : highlight === "pass"
        ? "text-[#1a7f37] font-semibold"
        : "text-[#1f2328] font-semibold";

  return (
    <div className="flex justify-between items-baseline py-2 border-b border-[#e5e7eb] last:border-b-0 text-sm">
      <span className="text-[#57606a]">{label}</span>
      <span className={`font-mono text-xs ${valueClass}`}>{value}</span>
    </div>
  );
}
