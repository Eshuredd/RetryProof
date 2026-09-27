import type { ReactNode } from "react";
import { StatRow } from "./StatRow";

export interface EvidenceStats {
  timestamp: string;
  deliveries: number;
  httpResponses: string;
  expectedEffects: number;
  actualEffects: number;
  observation: string;
}

interface ResultCardProps {
  heading: string;
  result: "FAIL" | "PASS";
  stats: EvidenceStats;
}

export function ResultCard({ heading, result, stats }: ResultCardProps) {
  const isFail = result === "FAIL";

  const headerBg = isFail ? "bg-[#ffebe9]" : "bg-[#dafbe1]";
  const headerText = isFail ? "text-[#cf222e]" : "text-[#1a7f37]";
  const badgeBg = isFail ? "bg-[#cf222e]" : "bg-[#1a7f37]";

  return (
    <div className="border border-[#e5e7eb] rounded-lg overflow-hidden">
      {/* Card header */}
      <div
        className={`${headerBg} ${headerText} flex items-center justify-between px-4 py-3 border-b border-[#e5e7eb]`}
      >
        <span className="text-xs font-semibold uppercase tracking-wider">
          {heading}
        </span>
        <span
          className={`${badgeBg} text-white text-[10px] font-bold tracking-wider px-2.5 py-0.5 rounded-full`}
        >
          {result}
        </span>
      </div>

      {/* Stats */}
      <div className="bg-white px-4 py-1">
        <StatRow label="Run timestamp" value={stats.timestamp} />
        <StatRow label="Deliveries" value={String(stats.deliveries)} />
        <StatRow label="HTTP responses" value={stats.httpResponses} />
        <StatRow label="Expected effects" value={String(stats.expectedEffects)} />
        <StatRow
          label="Actual effects"
          value={String(stats.actualEffects)}
          highlight={isFail ? "fail" : "pass"}
        />
        <StatRow label="Observation" value={stats.observation} />
      </div>
    </div>
  );
}
