import { Lock } from "lucide-react";

const SHA =
  "0af349e3d17312be5b8faa265e614c60ea40b448a11615157b0367999dde9e98";

export function ContractProof() {
  return (
    <section
      id="contract"
      style={{
        borderTop: "1px solid var(--border)",
        borderBottom: "1px solid var(--border)",
        background: "var(--surface)",
      }}
    >
      <div className="max-w-7xl mx-auto px-6 py-12">
        {/* Heading */}
        <div className="flex items-center gap-2 mb-6">
          <Lock size={16} style={{ color: "var(--accent)" }} />
          <h2
            className="font-bold text-lg"
            style={{ letterSpacing: "-0.02em", color: "var(--foreground)" }}
          >
            Same Frozen Contract
          </h2>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
          {/* Left: SHA display */}
          <div>
            <div
              className="text-xs font-mono font-semibold uppercase tracking-widest mb-3"
              style={{ color: "var(--muted)" }}
            >
              SHA-256
            </div>
            <div
              className="font-mono text-sm px-4 py-3 rounded-md break-all leading-relaxed"
              style={{
                background: "var(--surface-2)",
                color: "var(--foreground)",
                border: "1px solid var(--border)",
                wordBreak: "break-all",
              }}
            >
              {SHA}
            </div>
            <p
              className="text-xs mt-2"
              style={{ color: "var(--muted-2)" }}
              title="The scenario SHA-256 fingerprints the exact verification contract used for both runs."
            >
              Fingerprints the exact contract used for both runs. The scenario file was not
              modified between the FAIL and PASS runs.
            </p>
          </div>

          {/* Right: metadata */}
          <div className="space-y-4">
            <div>
              <div
                className="text-xs font-mono font-semibold uppercase tracking-widest mb-2"
                style={{ color: "var(--muted)" }}
              >
                Scenario
              </div>
              <div
                className="font-mono text-sm px-4 py-2.5 rounded-md"
                style={{
                  background: "var(--surface-2)",
                  color: "var(--foreground)",
                  border: "1px solid var(--border)",
                }}
              >
                notification_send_idempotency
              </div>
            </div>

            <div>
              <div
                className="text-xs font-mono font-semibold uppercase tracking-widest mb-2"
                style={{ color: "var(--muted)" }}
              >
                Contract file
              </div>
              <div
                className="font-mono text-sm px-4 py-2.5 rounded-md"
                style={{
                  background: "var(--surface-2)",
                  color: "var(--foreground)",
                  border: "1px solid var(--border)",
                }}
              >
                scenarios/notification_send.json
              </div>
            </div>

            <p
              className="text-sm leading-relaxed"
              style={{ color: "var(--muted)" }}
            >
              The verification contract was unchanged. Only the target
              application code was repaired. Matching SHA values in both
              evidence files prove no test was altered to make the repair pass.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
