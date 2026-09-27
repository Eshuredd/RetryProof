import {
  FileText,
  AlertCircle,
  Wrench,
  RotateCcw,
  ShieldCheck,
} from "lucide-react";

const STEPS = [
  {
    number: "01",
    icon: FileText,
    title: "Define Contract",
    description:
      "A scenario JSON file specifies the endpoint, delivery count, and the side-effect assertion. The file is fingerprinted by SHA-256.",
  },
  {
    number: "02",
    icon: AlertCircle,
    title: "Detect Failure",
    description:
      "RetryProof drives the unpatched application with 5 identical requests. The observation reveals 5 database rows instead of 1. Evidence is saved.",
  },
  {
    number: "03",
    icon: Wrench,
    title: "IBM Bob Repairs",
    description:
      "IBM Bob reads the FAIL evidence and application source, identifies the missing idempotency guard, and applies the fix.",
  },
  {
    number: "04",
    icon: RotateCcw,
    title: "Rerun Same Contract",
    description:
      "The identical frozen scenario is replayed against the repaired application. SHA-256 is unchanged — no human modifies the test.",
  },
  {
    number: "05",
    icon: ShieldCheck,
    title: "Generate Proof",
    description:
      "The PASS evidence shows sqlite_count = 1. Matching SHA values in both evidence files prove the repair — not assumed.",
  },
];

export function Workflow() {
  return (
    <section className="max-w-7xl mx-auto px-6 py-16">
      {/* Heading */}
      <div className="mb-10">
        <div
          className="text-xs font-mono font-semibold uppercase tracking-widest mb-2"
          style={{ color: "var(--muted)" }}
        >
          How It Works
        </div>
        <h2
          className="font-bold text-2xl"
          style={{ letterSpacing: "-0.025em", color: "var(--foreground)" }}
        >
          Five steps from failure to proof
        </h2>
      </div>

      {/* Desktop: horizontal flow */}
      <div className="hidden lg:flex items-start gap-0">
        {STEPS.map((step, i) => {
          const Icon = step.icon;
          return (
            <div key={step.number} className="flex items-start flex-1">
              <div className="flex flex-col flex-1">
                {/* Step box */}
                <div
                  className="rounded-lg p-5"
                  style={{
                    background: "var(--surface)",
                    border: "1px solid var(--border)",
                  }}
                >
                  <div className="flex items-center gap-2 mb-3">
                    <div
                      className="w-8 h-8 rounded flex items-center justify-center flex-shrink-0"
                      style={{
                        background: "var(--surface-2)",
                        border: "1px solid var(--border)",
                      }}
                    >
                      <Icon size={14} style={{ color: "var(--accent)" }} />
                    </div>
                    <span
                      className="font-mono text-xs font-bold"
                      style={{ color: "var(--muted-2)" }}
                    >
                      {step.number}
                    </span>
                  </div>
                  <div
                    className="font-semibold text-sm mb-2"
                    style={{ color: "var(--foreground)" }}
                  >
                    {step.title}
                  </div>
                  <p
                    className="text-xs leading-relaxed"
                    style={{ color: "var(--muted)" }}
                  >
                    {step.description}
                  </p>
                </div>
              </div>
              {/* Connector */}
              {i < STEPS.length - 1 && (
                <div
                  className="flex items-start mt-9 mx-1 flex-shrink-0"
                  style={{ color: "var(--muted-2)" }}
                >
                  <svg
                    width="20"
                    height="2"
                    viewBox="0 0 20 2"
                    fill="none"
                    aria-hidden="true"
                  >
                    <line
                      x1="0"
                      y1="1"
                      x2="20"
                      y2="1"
                      stroke="currentColor"
                      strokeWidth="1.5"
                      strokeDasharray="4 2"
                    />
                  </svg>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Mobile: vertical flow */}
      <div className="lg:hidden flex flex-col gap-3">
        {STEPS.map((step) => {
          const Icon = step.icon;
          return (
            <div
              key={step.number}
              className="rounded-lg p-4 flex gap-4"
              style={{
                background: "var(--surface)",
                border: "1px solid var(--border)",
              }}
            >
              <div
                className="w-9 h-9 rounded flex items-center justify-center flex-shrink-0 mt-0.5"
                style={{
                  background: "var(--surface-2)",
                  border: "1px solid var(--border)",
                }}
              >
                <Icon size={14} style={{ color: "var(--accent)" }} />
              </div>
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span
                    className="font-mono text-xs font-bold"
                    style={{ color: "var(--muted-2)" }}
                  >
                    {step.number}
                  </span>
                  <span
                    className="font-semibold text-sm"
                    style={{ color: "var(--foreground)" }}
                  >
                    {step.title}
                  </span>
                </div>
                <p
                  className="text-xs leading-relaxed"
                  style={{ color: "var(--muted)" }}
                >
                  {step.description}
                </p>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
