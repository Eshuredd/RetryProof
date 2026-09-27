interface ShaBlockProps {
  sha: string;
  note?: string;
}

export function ShaBlock({ sha, note }: ShaBlockProps) {
  return (
    <div className="flex gap-4 items-start bg-[#f7f8fa] border border-[#e5e7eb] rounded-lg p-4">
      {/* Lock icon */}
      <div className="flex-shrink-0 w-8 h-8 rounded-md bg-[#e5e7eb] flex items-center justify-center">
        <svg
          width="16"
          height="16"
          viewBox="0 0 16 16"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <rect
            x="3"
            y="7"
            width="10"
            height="8"
            rx="1.5"
            stroke="#57606a"
            strokeWidth="1.4"
          />
          <path
            d="M5.5 7V5a2.5 2.5 0 0 1 5 0v2"
            stroke="#57606a"
            strokeWidth="1.4"
            strokeLinecap="round"
          />
        </svg>
      </div>

      <div className="min-w-0">
        <p className="text-[11px] font-semibold uppercase tracking-wider text-[#57606a] mb-1">
          SHA-256 — same contract used for both runs
        </p>
        <p className="font-mono text-sm break-all text-[#1f2328]">{sha}</p>
        {note && (
          <p className="mt-1 text-xs text-[#57606a]">{note}</p>
        )}
      </div>
    </div>
  );
}
