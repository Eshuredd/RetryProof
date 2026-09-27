const METRICS = [
  {
    value: "5",
    label: "Deliveries",
    sub: "retries per run",
  },
  {
    value: "1",
    label: "Expected effect",
    sub: "per message",
  },
  {
    value: "5 → 1",
    label: "Actual effects",
    sub: "before → after repair",
    highlight: true,
  },
  {
    value: "SAME",
    label: "Contract SHA",
    sub: "unchanged between runs",
  },
];

export function MetricsStrip() {
  return (
    <section
      style={{
        borderTop: "1px solid var(--border)",
        borderBottom: "1px solid var(--border)",
        background: "var(--surface)",
      }}
    >
      <div className="max-w-7xl mx-auto px-6 py-6">
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-0">
          {METRICS.map((m, i) => (
            <div
              key={m.label}
              className="flex flex-col py-4 px-6"
              style={{
                borderRight:
                  i < METRICS.length - 1 ? "1px solid var(--border)" : undefined,
              }}
            >
              <span
                className="font-mono font-bold leading-none mb-1.5"
                style={{
                  fontSize: "1.75rem",
                  color: m.highlight ? "var(--accent)" : "var(--foreground)",
                  letterSpacing: "-0.02em",
                }}
              >
                {m.value}
              </span>
              <span
                className="text-sm font-medium"
                style={{ color: "var(--foreground)" }}
              >
                {m.label}
              </span>
              <span
                className="text-xs mt-0.5"
                style={{ color: "var(--muted-2)" }}
              >
                {m.sub}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
