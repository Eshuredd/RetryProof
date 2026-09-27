"use client";

const TERMINAL_LINES = [
  { type: "prompt", text: "$ python -m retryproof run scenarios/notification_send.json" },
  { type: "blank" },
  { type: "info", text: "Scenario  notification_send_idempotency" },
  { type: "info", text: "SHA-256   0af349e3...9dde9e98" },
  { type: "info", text: "Deliveries  5" },
  { type: "blank" },
  { type: "section", text: "─── BEFORE REPAIR ────────────────────────────────" },
  { type: "normal", text: "Running 5 retries against target..." },
  { type: "normal", text: "HTTP  201  201  201  201  201" },
  { type: "normal", text: "DB rows expected  1" },
  { type: "normal", text: "DB rows actual    5" },
  { type: "fail", text: "▶  RESULT: FAIL" },
  { type: "blank" },
  { type: "divider", text: "  IBM Bob repairs target application" },
  { type: "blank" },
  { type: "section", text: "─── AFTER REPAIR ─────────────────────────────────" },
  { type: "normal", text: "Running 5 retries against target..." },
  { type: "normal", text: "HTTP  201  201  201  201  201" },
  { type: "normal", text: "DB rows expected  1" },
  { type: "normal", text: "DB rows actual    1" },
  { type: "pass", text: "▶  RESULT: PASS" },
  { type: "blank" },
  { type: "sha", text: "Contract SHA  0af349e3d17312be5b8faa265e614c60ea40b448a11615157b0367999dde9e98" },
];

type LineType = "prompt" | "blank" | "info" | "section" | "normal" | "fail" | "pass" | "divider" | "sha";

function TerminalLine({ type, text }: { type: LineType; text?: string }) {
  if (type === "blank") return <div className="h-2" />;

  const colors: Record<string, string> = {
    prompt: "#a5b4fc",
    info: "#8892a4",
    section: "#5a6478",
    normal: "#c9d1d9",
    fail: "#ef4444",
    pass: "#22c55e",
    divider: "#3b82f6",
    sha: "#8892a4",
  };

  return (
    <div
      className="font-mono text-xs leading-5 whitespace-pre-wrap break-all"
      style={{ color: colors[type] || "#c9d1d9" }}
    >
      {text}
    </div>
  );
}

export function TerminalDemo() {
  return (
    <div
      className="rounded-lg overflow-hidden"
      style={{
        background: "#0a0c10",
        border: "1px solid var(--border)",
      }}
    >
      {/* Terminal chrome */}
      <div
        className="flex items-center gap-1.5 px-4 py-3"
        style={{
          background: "#111419",
          borderBottom: "1px solid var(--border)",
        }}
      >
        <span className="w-3 h-3 rounded-full" style={{ background: "#ff5f57" }} />
        <span className="w-3 h-3 rounded-full" style={{ background: "#febc2e" }} />
        <span className="w-3 h-3 rounded-full" style={{ background: "#28c840" }} />
        <span
          className="ml-auto font-mono text-xs"
          style={{ color: "var(--muted-2)" }}
        >
          retryproof
        </span>
      </div>

      {/* Terminal body */}
      <div className="px-4 py-4 space-y-0.5">
        {TERMINAL_LINES.map((line, i) => (
          <TerminalLine key={i} type={line.type as LineType} text={line.text} />
        ))}
        <div className="flex items-center gap-1 mt-2">
          <span className="font-mono text-xs" style={{ color: "#a5b4fc" }}>$ </span>
          <span
            className="inline-block w-2 h-4"
            style={{ background: "#a5b4fc", opacity: 0.8 }}
          />
        </div>
      </div>
    </div>
  );
}
