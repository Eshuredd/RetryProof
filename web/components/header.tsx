import { GitFork, ShieldCheck } from "lucide-react";

export function Header() {
  return (
    <header
      style={{
        borderBottom: "1px solid var(--border)",
        background: "var(--background)",
      }}
      className="sticky top-0 z-50"
    >
      <div
        className="max-w-7xl mx-auto px-6 flex items-center justify-between"
        style={{ height: "52px" }}
      >
        {/* Logo */}
        <div className="flex items-center gap-3">
          <span
            className="text-base font-bold tracking-tight select-none"
            style={{ letterSpacing: "-0.02em" }}
          >
            <span style={{ color: "var(--foreground)" }}>Retry</span>
            <span style={{ color: "var(--accent)" }}>Proof</span>
          </span>
          <span
            className="hidden sm:inline-flex items-center gap-1 text-xs font-mono px-2 py-0.5 rounded"
            style={{
              background: "var(--surface-2)",
              color: "var(--muted)",
              border: "1px solid var(--border)",
            }}
          >
            v0.1.0
          </span>
        </div>

        {/* Right side actions */}
        <div className="flex items-center gap-3">
          {/* Evidence Verified badge */}
          <span
            className="hidden md:inline-flex items-center gap-1.5 text-xs px-2.5 py-1 rounded-md font-medium"
            style={{
              background: "var(--pass-dim)",
              color: "var(--pass)",
              border: "1px solid var(--pass-border)",
            }}
          >
            <ShieldCheck size={12} strokeWidth={2.5} />
            Evidence Verified
          </span>

          {/* GitHub button */}
          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 text-sm font-medium px-3 py-1.5 rounded-md transition-colors"
            style={{
              background: "var(--surface-2)",
              color: "var(--muted)",
              border: "1px solid var(--border)",
            }}
            aria-label="View on GitHub"
          >
            <GitFork size={14} />
            <span className="hidden sm:inline">GitHub</span>
          </a>
        </div>
      </div>
    </header>
  );
}
