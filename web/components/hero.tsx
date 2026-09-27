import { TerminalDemo } from "./terminal-demo";

export function Hero() {
  return (
    <section
      className="max-w-7xl mx-auto px-6 py-16 lg:py-20"
    >
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-16 items-start">
        {/* Left: copy */}
        <div className="flex flex-col justify-center">
          {/* Label */}
          <div
            className="inline-flex items-center gap-2 text-xs font-mono font-medium px-2.5 py-1 rounded mb-6 self-start"
            style={{
              background: "var(--accent-dim)",
              color: "var(--accent)",
              border: "1px solid rgba(59,130,246,0.25)",
            }}
          >
            IBM Bob 2.0 Hackathon · 2026
          </div>

          {/* Headline */}
          <h1
            className="font-bold leading-tight mb-5"
            style={{
              fontSize: "clamp(2rem, 4vw, 3rem)",
              letterSpacing: "-0.03em",
              color: "var(--foreground)",
            }}
          >
            Prove the fix.
            <br />
            <span style={{ color: "var(--muted)" }}>
              Don&apos;t trust the agent.
            </span>
          </h1>

          {/* Supporting text */}
          <p
            className="text-base mb-8 leading-relaxed max-w-lg"
            style={{ color: "var(--muted)" }}
          >
            RetryProof reproduces retry failures and reruns the exact same
            frozen contract after IBM Bob repairs the application. Matching
            SHA-256 values prove the verifier was never touched.
          </p>

          {/* CTAs */}
          <div className="flex flex-wrap gap-3">
            <a
              href="#proof"
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-md text-sm font-semibold transition-opacity hover:opacity-90"
              style={{
                background: "var(--accent)",
                color: "#fff",
              }}
            >
              View verification proof
            </a>
            <a
              href="#evidence"
              className="inline-flex items-center gap-2 px-4 py-2.5 rounded-md text-sm font-semibold transition-colors"
              style={{
                background: "var(--surface-2)",
                color: "var(--muted)",
                border: "1px solid var(--border)",
              }}
            >
              View evidence
            </a>
          </div>
        </div>

        {/* Right: terminal */}
        <div>
          <TerminalDemo />
        </div>
      </div>
    </section>
  );
}
