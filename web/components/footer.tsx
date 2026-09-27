import { GitFork } from "lucide-react";

export function Footer() {
  return (
    <footer
      style={{
        borderTop: "1px solid var(--border)",
        background: "var(--background)",
      }}
    >
      <div className="max-w-7xl mx-auto px-6 py-8 flex flex-col sm:flex-row items-center justify-between gap-4">
        {/* Branding */}
        <div className="flex flex-col items-center sm:items-start gap-1">
          <span
            className="font-bold text-sm tracking-tight"
            style={{ letterSpacing: "-0.02em" }}
          >
            <span style={{ color: "var(--foreground)" }}>Retry</span>
            <span style={{ color: "var(--accent)" }}>Proof</span>
          </span>
          <span
            className="text-xs"
            style={{ color: "var(--muted-2)" }}
          >
            Independent verification for retry-safe repairs.
          </span>
        </div>

        {/* Right */}
        <div className="flex items-center gap-4">
          <span
            className="text-xs"
            style={{ color: "var(--muted-2)" }}
          >
            IBM Bob 2.0 Hackathon &middot; 2026
          </span>
          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="GitHub"
            className="transition-opacity hover:opacity-70"
            style={{ color: "var(--muted-2)" }}
          >
            <GitFork size={16} />
          </a>
        </div>
      </div>
    </footer>
  );
}
