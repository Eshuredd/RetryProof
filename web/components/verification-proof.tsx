import { ArrowRight, Wrench } from "lucide-react";

function ResultBadge({ result }: { result: "FAIL" | "PASS" }) {
  const isFail = result === "FAIL";
  return (
    <span
      className="inline-flex items-center px-3 py-1 rounded text-sm font-mono font-bold tracking-widest"
      style={{
        background: isFail ? "var(--fail-dim)" : "var(--pass-dim)",
        color: isFail ? "var(--fail)" : "var(--pass)",
        border: `1px solid ${isFail ? "var(--fail-border)" : "var(--pass-border)"}`,
      }}
    >
      {result}
    </span>
  );
}

function BeforeCard() {
  return (
    <div
      className="rounded-lg p-6 flex flex-col gap-5 h-full"
      style={{
        background: "var(--surface)",
        border: "1px solid var(--fail-border)",
      }}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <span
          className="text-xs font-mono font-semibold uppercase tracking-widest"
          style={{ color: "var(--muted)" }}
        >
          Before Repair
        </span>
        <ResultBadge result="FAIL" />
      </div>

      {/* Big number */}
      <div>
        <div
          className="font-mono font-bold leading-none"
          style={{ fontSize: "5rem", color: "var(--fail)", letterSpacing: "-0.04em" }}
        >
          5
        </div>
        <div
          className="text-sm mt-1 font-medium"
          style={{ color: "var(--muted)" }}
        >
          Actual effects
        </div>
      </div>

      {/* Stats */}
      <div className="space-y-3">
        <div className="flex justify-between items-center">
          <span className="text-sm" style={{ color: "var(--muted)" }}>
            Expected
          </span>
          <span
            className="font-mono text-sm font-semibold"
            style={{ color: "var(--foreground)" }}
          >
            1
          </span>
        </div>
        <div
          className="h-px"
          style={{ background: "var(--border-subtle)" }}
        />
        <div className="flex justify-between items-center">
          <span className="text-sm" style={{ color: "var(--muted)" }}>
            Deliveries
          </span>
          <span
            className="font-mono text-sm font-semibold"
            style={{ color: "var(--foreground)" }}
          >
            5
          </span>
        </div>
        <div
          className="h-px"
          style={{ background: "var(--border-subtle)" }}
        />
        <div className="flex justify-between items-center">
          <span className="text-sm" style={{ color: "var(--muted)" }}>
            HTTP responses
          </span>
          <span
            className="font-mono text-sm font-semibold"
            style={{ color: "var(--foreground)" }}
          >
            5 × 201
          </span>
        </div>
      </div>

      {/* Annotation */}
      <p
        className="text-sm leading-relaxed mt-auto pt-3"
        style={{
          color: "var(--muted-2)",
          borderTop: "1px solid var(--border-subtle)",
        }}
      >
        Five retries produced five persistent side effects. The application
        is not idempotent.
      </p>
    </div>
  );
}

function RepairCard() {
  return (
    <div
      className="rounded-lg p-6 flex flex-col items-center justify-center gap-5 h-full text-center"
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border)",
      }}
    >
      {/* Icon */}
      <div
        className="w-12 h-12 rounded-lg flex items-center justify-center"
        style={{
          background: "var(--accent-dim)",
          border: "1px solid rgba(59,130,246,0.25)",
        }}
      >
        <Wrench size={20} style={{ color: "var(--accent)" }} />
      </div>

      {/* Label */}
      <div>
        <div
          className="text-xs font-mono font-semibold uppercase tracking-widest mb-1"
          style={{ color: "var(--muted)" }}
        >
          Repaired by
        </div>
        <div
          className="font-bold text-lg"
          style={{ color: "var(--foreground)", letterSpacing: "-0.02em" }}
        >
          IBM Bob
        </div>
      </div>

      {/* Flow arrows */}
      <div className="flex flex-col items-center gap-2">
        <ArrowRight
          size={20}
          style={{ color: "var(--accent)", transform: "rotate(90deg)" }}
        />
      </div>

      {/* Description */}
      <p
        className="text-sm leading-relaxed"
        style={{ color: "var(--muted-2)" }}
      >
        Target application repaired.
        <br />
        Verification contract unchanged.
      </p>

      {/* Contract note */}
      <div
        className="text-xs font-mono px-3 py-2 rounded w-full"
        style={{
          background: "var(--surface-2)",
          color: "var(--muted-2)",
          border: "1px solid var(--border)",
        }}
      >
        scenario SHA identical
      </div>
    </div>
  );
}

function AfterCard() {
  return (
    <div
      className="rounded-lg p-6 flex flex-col gap-5 h-full"
      style={{
        background: "var(--surface)",
        border: "1px solid var(--pass-border)",
      }}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <span
          className="text-xs font-mono font-semibold uppercase tracking-widest"
          style={{ color: "var(--muted)" }}
        >
          After Repair
        </span>
        <ResultBadge result="PASS" />
      </div>

      {/* Big number */}
      <div>
        <div
          className="font-mono font-bold leading-none"
          style={{ fontSize: "5rem", color: "var(--pass)", letterSpacing: "-0.04em" }}
        >
          1
        </div>
        <div
          className="text-sm mt-1 font-medium"
          style={{ color: "var(--muted)" }}
        >
          Actual effects
        </div>
      </div>

      {/* Stats */}
      <div className="space-y-3">
        <div className="flex justify-between items-center">
          <span className="text-sm" style={{ color: "var(--muted)" }}>
            Expected
          </span>
          <span
            className="font-mono text-sm font-semibold"
            style={{ color: "var(--foreground)" }}
          >
            1
          </span>
        </div>
        <div
          className="h-px"
          style={{ background: "var(--border-subtle)" }}
        />
        <div className="flex justify-between items-center">
          <span className="text-sm" style={{ color: "var(--muted)" }}>
            Deliveries
          </span>
          <span
            className="font-mono text-sm font-semibold"
            style={{ color: "var(--foreground)" }}
          >
            5
          </span>
        </div>
        <div
          className="h-px"
          style={{ background: "var(--border-subtle)" }}
        />
        <div className="flex justify-between items-center">
          <span className="text-sm" style={{ color: "var(--muted)" }}>
            HTTP responses
          </span>
          <span
            className="font-mono text-sm font-semibold"
            style={{ color: "var(--foreground)" }}
          >
            5 × 201
          </span>
        </div>
      </div>

      {/* Annotation */}
      <p
        className="text-sm leading-relaxed mt-auto pt-3"
        style={{
          color: "var(--muted-2)",
          borderTop: "1px solid var(--border-subtle)",
        }}
      >
        Five retries now produce exactly one persistent side effect. The
        application is idempotent.
      </p>
    </div>
  );
}

export function VerificationProof() {
  return (
    <section id="proof" className="max-w-7xl mx-auto px-6 py-16">
      {/* Section heading */}
      <div className="mb-10">
        <div
          className="text-xs font-mono font-semibold uppercase tracking-widest mb-2"
          style={{ color: "var(--muted)" }}
        >
          Verification Proof
        </div>
        <h2
          className="font-bold text-2xl"
          style={{ letterSpacing: "-0.025em", color: "var(--foreground)" }}
        >
          FAIL &rarr; IBM Bob Repair &rarr; PASS
        </h2>
        <p
          className="text-sm mt-2 max-w-lg"
          style={{ color: "var(--muted)" }}
        >
          The same frozen contract, run twice. The only change was the
          target application code.
        </p>
      </div>

      {/* Three-column layout */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 items-stretch">
        <BeforeCard />
        <RepairCard />
        <AfterCard />
      </div>
    </section>
  );
}
