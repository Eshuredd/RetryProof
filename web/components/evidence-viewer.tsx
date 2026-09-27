"use client";

import { useState } from "react";

type EvidenceResult = "FAIL" | "PASS";
type HighlightColor = "fail" | "pass";

interface EvidenceField {
  key: string;
  value: string;
  highlight?: HighlightColor;
}

interface Evidence {
  file: string;
  timestamp: string;
  result: EvidenceResult;
  scenario_sha256: string;
  fields: EvidenceField[];
  http_responses: string[];
}

const BEFORE_EVIDENCE: Evidence = {
  file: "evidence/notification_send_idempotency_20260927T091102_557773Z_FAIL_0af349e3.json",
  timestamp: "2026-09-27T09:11:02.557773+00:00",
  result: "FAIL",
  scenario_sha256:
    "0af349e3d17312be5b8faa265e614c60ea40b448a11615157b0367999dde9e98",
  fields: [
    { key: "scenario_name", value: "notification_send_idempotency" },
    { key: "deliveries", value: "5" },
    { key: "expected_after", value: "1" },
    { key: "actual_after", value: "5" },
    { key: "result", value: "FAIL", highlight: "fail" },
    {
      key: "observation.query",
      value: "SELECT COUNT(*) FROM email_jobs WHERE message_id = ?",
    },
    { key: "observation.type", value: "sqlite_count" },
    { key: "precondition.passed", value: "true" },
  ],
  http_responses: ["201", "201", "201", "201", "201"],
};

const AFTER_EVIDENCE: Evidence = {
  file: "evidence/notification_send_idempotency_20260927T134753_196405Z_PASS_0af349e3.json",
  timestamp: "2026-09-27T13:47:53.196405+00:00",
  result: "PASS",
  scenario_sha256:
    "0af349e3d17312be5b8faa265e614c60ea40b448a11615157b0367999dde9e98",
  fields: [
    { key: "scenario_name", value: "notification_send_idempotency" },
    { key: "deliveries", value: "5" },
    { key: "expected_after", value: "1" },
    { key: "actual_after", value: "1" },
    { key: "result", value: "PASS", highlight: "pass" },
    {
      key: "observation.query",
      value: "SELECT COUNT(*) FROM email_jobs WHERE message_id = ?",
    },
    { key: "observation.type", value: "sqlite_count" },
    { key: "precondition.passed", value: "true" },
  ],
  http_responses: ["201", "201", "201", "201", "201"],
};

function EvidencePanel({ ev }: { ev: Evidence }) {
  const isFail = ev.result === "FAIL";
  return (
    <div className="space-y-5">
      {/* File path */}
      <div>
        <div
          className="text-xs font-mono font-semibold uppercase tracking-widest mb-2"
          style={{ color: "var(--muted)" }}
        >
          Evidence File
        </div>
        <div
          className="font-mono text-xs px-4 py-3 rounded-md break-all leading-relaxed"
          style={{
            background: "var(--surface-2)",
            color: "var(--foreground)",
            border: "1px solid var(--border)",
          }}
        >
          {ev.file}
        </div>
      </div>

      {/* Timestamp + Result */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <div
            className="text-xs font-mono font-semibold uppercase tracking-widest mb-2"
            style={{ color: "var(--muted)" }}
          >
            Timestamp
          </div>
          <div
            className="font-mono text-xs px-3 py-2 rounded-md"
            style={{
              background: "var(--surface-2)",
              color: "var(--foreground)",
              border: "1px solid var(--border)",
            }}
          >
            {ev.timestamp}
          </div>
        </div>
        <div>
          <div
            className="text-xs font-mono font-semibold uppercase tracking-widest mb-2"
            style={{ color: "var(--muted)" }}
          >
            Result
          </div>
          <div
            className="font-mono text-sm font-bold px-3 py-2 rounded-md inline-flex"
            style={{
              background: isFail ? "var(--fail-dim)" : "var(--pass-dim)",
              color: isFail ? "var(--fail)" : "var(--pass)",
              border: `1px solid ${isFail ? "var(--fail-border)" : "var(--pass-border)"}`,
            }}
          >
            {ev.result}
          </div>
        </div>
      </div>

      {/* Key/value table */}
      <div>
        <div
          className="text-xs font-mono font-semibold uppercase tracking-widest mb-2"
          style={{ color: "var(--muted)" }}
        >
          Key Values
        </div>
        <div
          className="rounded-md overflow-hidden"
          style={{ border: "1px solid var(--border)" }}
        >
          {ev.fields.map((field, i) => (
            <div
              key={field.key}
              className="flex items-center gap-4 px-4 py-2.5 text-xs"
              style={{
                background: i % 2 === 0 ? "var(--surface-2)" : "var(--surface)",
                borderBottom:
                  i < ev.fields.length - 1 ? "1px solid var(--border-subtle)" : undefined,
              }}
            >
              <span
                className="font-mono w-40 flex-shrink-0"
                style={{ color: "var(--muted)" }}
              >
                {field.key}
              </span>
              <span
                className="font-mono font-semibold"
                style={{
                  color:
                    field.highlight === "fail"
                      ? "var(--fail)"
                      : field.highlight === "pass"
                      ? "var(--pass)"
                      : "var(--foreground)",
                }}
              >
                {field.value}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* HTTP responses */}
      <div>
        <div
          className="text-xs font-mono font-semibold uppercase tracking-widest mb-2"
          style={{ color: "var(--muted)" }}
        >
          HTTP Delivery Log
        </div>
        <div className="flex gap-2 flex-wrap">
          {ev.http_responses.map((code, i) => (
            <span
              key={i}
              className="font-mono text-xs px-2.5 py-1 rounded"
              style={{
                background: "var(--pass-dim)",
                color: "var(--pass)",
                border: "1px solid var(--pass-border)",
              }}
            >
              {code}
            </span>
          ))}
        </div>
      </div>

      {/* SHA */}
      <div>
        <div
          className="text-xs font-mono font-semibold uppercase tracking-widest mb-2"
          style={{ color: "var(--muted)" }}
        >
          Scenario SHA-256
        </div>
        <div
          className="font-mono text-xs px-4 py-2.5 rounded-md break-all"
          style={{
            background: "var(--surface-2)",
            color: "var(--foreground)",
            border: "1px solid var(--border)",
          }}
        >
          {ev.scenario_sha256}
        </div>
      </div>
    </div>
  );
}

export function EvidenceViewer() {
  const [active, setActive] = useState<"before" | "after">("before");

  return (
    <section
      id="evidence"
      style={{
        borderTop: "1px solid var(--border)",
        background: "var(--surface)",
      }}
    >
      <div className="max-w-7xl mx-auto px-6 py-16">
        {/* Heading */}
        <div className="mb-8">
          <div
            className="text-xs font-mono font-semibold uppercase tracking-widest mb-2"
            style={{ color: "var(--muted)" }}
          >
            Evidence
          </div>
          <h2
            className="font-bold text-2xl"
            style={{ letterSpacing: "-0.025em", color: "var(--foreground)" }}
          >
            Inspectable verification records
          </h2>
          <p
            className="text-sm mt-2"
            style={{ color: "var(--muted)" }}
          >
            Both evidence files are written by RetryProof and never modified.
          </p>
        </div>

        {/* Tabs */}
        <div
          className="flex gap-1 mb-6 p-1 rounded-lg inline-flex"
          style={{
            background: "var(--surface-2)",
            border: "1px solid var(--border)",
          }}
        >
          {(["before", "after"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActive(tab)}
              className="px-4 py-2 rounded-md text-sm font-medium transition-all"
              style={{
                background: active === tab ? "var(--surface)" : "transparent",
                color:
                  active === tab ? "var(--foreground)" : "var(--muted)",
                border:
                  active === tab ? "1px solid var(--border)" : "1px solid transparent",
              }}
            >
              {tab === "before" ? (
                <>
                  Before Evidence{" "}
                  <span
                    className="ml-1.5 text-xs font-mono font-bold"
                    style={{ color: "var(--fail)" }}
                  >
                    FAIL
                  </span>
                </>
              ) : (
                <>
                  After Evidence{" "}
                  <span
                    className="ml-1.5 text-xs font-mono font-bold"
                    style={{ color: "var(--pass)" }}
                  >
                    PASS
                  </span>
                </>
              )}
            </button>
          ))}
        </div>

        {/* Panel */}
        <EvidencePanel ev={active === "before" ? BEFORE_EVIDENCE : AFTER_EVIDENCE} />
      </div>
    </section>
  );
}
