"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, SummaryResponse, TranscriptItem, StrengthGapItem } from "@/lib/api";

// ── Score helpers ─────────────────────────────────────────────────────────────

function scoreColor(s: number): string {
  return s >= 4
    ? "var(--color-score-strong)"
    : s >= 3
    ? "var(--color-score-mid)"
    : "var(--color-score-weak)";
}

function scoreBg(s: number): string {
  return s >= 4
    ? "rgba(34,197,94,0.12)"
    : s >= 3
    ? "rgba(245,158,11,0.12)"
    : "rgba(239,68,68,0.12)";
}

function ScoreCircle({ score }: { score: number }) {
  return (
    <div
      style={{
        width: 48,
        height: 48,
        borderRadius: "50%",
        background: scoreBg(score),
        border: `2px solid ${scoreColor(score)}40`,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontWeight: 700,
        fontSize: 18,
        color: scoreColor(score),
        flexShrink: 0,
      }}
    >
      {score}
    </div>
  );
}

// ── Strength / Gap card ───────────────────────────────────────────────────────

function AnalysisCard({
  item,
  variant,
}: {
  item: StrengthGapItem | string;
  variant: "strength" | "gap";
}) {
  const isStrength = variant === "strength";
  const accent = isStrength ? "var(--color-score-strong)" : "var(--color-score-weak)";
  const bg = isStrength ? "rgba(34,197,94,0.05)" : "rgba(239,68,68,0.05)";
  const border = isStrength ? "rgba(34,197,94,0.18)" : "rgba(239,68,68,0.15)";
  const icon = isStrength ? "✓" : "↗";

  const area = typeof item === "string" ? item : item.area;
  const detail = typeof item === "string" ? null : item.detail;

  return (
    <li
      style={{
        background: bg,
        border: `1px solid ${border}`,
        borderRadius: 10,
        padding: "12px 14px",
        display: "flex",
        gap: 10,
        alignItems: "flex-start",
      }}
    >
      <span style={{ color: accent, fontWeight: 700, flexShrink: 0, fontSize: 13 }}>{icon}</span>
      <div>
        <div style={{ fontWeight: 600, fontSize: 14, color: "var(--text-primary)", marginBottom: detail ? 4 : 0 }}>
          {area}
        </div>
        {detail && (
          <div style={{ fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.6 }}>
            {detail}
          </div>
        )}
      </div>
    </li>
  );
}

// ── Transcript card ───────────────────────────────────────────────────────────

function TranscriptCard({ item }: { item: TranscriptItem }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="glass-card" style={{ padding: 24, display: "flex", flexDirection: "column", gap: 16 }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "flex-start", gap: 16 }}>
        <ScoreCircle score={item.score} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
            <span style={{ fontSize: 13, color: "var(--text-muted)" }}>Q{item.order_index}</span>
            <span className={`difficulty-badge difficulty-${item.difficulty}`}>{item.difficulty}</span>
            <span className="topic-pill">{item.topic}</span>
          </div>
          <p style={{ fontWeight: 600, fontSize: 16, lineHeight: 1.5, marginBottom: 8 }}>{item.question}</p>
          <p style={{ fontSize: 14, color: "var(--text-secondary)", lineHeight: 1.6 }}>
            <span style={{ color: "var(--text-muted)" }}>Your answer: </span>
            {item.answer}
          </p>
        </div>
      </div>

      {/* Feedback */}
      <div
        style={{
          background: "rgba(255,255,255,0.03)",
          borderRadius: 10,
          padding: "12px 16px",
          fontSize: 14,
          color: "var(--text-secondary)",
          lineHeight: 1.6,
        }}
      >
        <span style={{ color: "#FDBA8C", fontWeight: 600 }}>Feedback: </span>
        {item.feedback}
      </div>

      {/* Traceability */}
      {(item.source_chunk_ids?.length > 0 || item.rationale) && (
        <button
          onClick={() => setOpen(!open)}
          style={{
            background: "transparent",
            border: "1px solid rgba(224,90,54,0.22)",
            borderRadius: 8,
            padding: "8px 14px",
            color: "#FDBA8C",
            fontSize: 13,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: 6,
            alignSelf: "flex-start",
            transition: "border-color 0.15s",
          }}
        >
          <span style={{ transform: open ? "rotate(90deg)" : "rotate(0deg)", transition: "transform 0.2s", display: "inline-block" }}>▶</span>
          Why this was asked
        </button>
      )}

      {open && (
        <div
          className="page-enter"
          style={{
            background: "rgba(224,90,54,0.05)",
            border: "1px solid rgba(224,90,54,0.15)",
            borderRadius: 10,
            padding: 16,
            fontSize: 13,
          }}
        >
          {item.rationale && (
            <div style={{ marginBottom: 12 }}>
              <span style={{ color: "#FDBA8C", fontWeight: 600 }}>Rationale: </span>
              <span style={{ color: "var(--text-secondary)" }}>{item.rationale}</span>
            </div>
          )}
          {item.source_chunk_ids?.length > 0 && (
            <div>
              <span style={{ color: "#FDBA8C", fontWeight: 600 }}>Grounded in: </span>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 6 }}>
                {item.source_chunk_ids.map((id) => (
                  <span
                    key={id}
                    style={{
                      background: "rgba(224,90,54,0.1)",
                      border: "1px solid rgba(224,90,54,0.2)",
                      borderRadius: 6,
                      padding: "2px 8px",
                      fontFamily: "monospace",
                      fontSize: 11,
                      color: "#FDBA8C",
                    }}
                  >
                    {id}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function SummaryPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = Number(params.sessionId);

  const [summary, setSummary] = useState<SummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .getSummary(sessionId)
      .then(setSummary)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : "Failed to load summary."))
      .finally(() => setLoading(false));
  }, [sessionId]);

  if (loading) {
    return (
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 16 }}>
        <div className="spinner" style={{ width: 40, height: 40 }} />
        <p style={{ color: "var(--text-secondary)" }}>Loading your results…</p>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 16 }}>
        <p style={{ color: "var(--color-score-weak)", fontSize: 16 }}>{error}</p>
        <button className="btn-primary" onClick={() => router.push("/")}>Return Home</button>
      </div>
    );
  }

  if (!summary) return null;

  const pct = Math.round((summary.overall_score / 5) * 100);
  const overallColor = scoreColor(summary.overall_score);

  return (
    <main className="page-enter" style={{ minHeight: "100vh", padding: "40px 16px 80px" }}>
      <div style={{ maxWidth: 800, margin: "0 auto" }}>

        {/* Header */}
        <div style={{ textAlign: "center", marginBottom: 48 }}>
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 8,
              background: "rgba(224,90,54,0.1)",
              border: "1px solid rgba(224,90,54,0.25)",
              borderRadius: 99,
              padding: "6px 16px",
              marginBottom: 20,
              fontSize: 14,
              color: "#FDBA8C",
            }}
          >
            ✦ Interview Complete
          </div>
          <h1 className="gradient-text" style={{ fontSize: 40, fontWeight: 800, marginBottom: 12 }}>
            Your Results
          </h1>
          <p style={{ color: "var(--text-secondary)", maxWidth: 500, margin: "0 auto", lineHeight: 1.6 }}>
            {summary.summary_text}
          </p>
        </div>

        {/* Score + analysis */}
        <div style={{ display: "grid", gridTemplateColumns: "200px 1fr", gap: 20, marginBottom: 32 }}>
          {/* Score circle */}
          <div
            className="glass-card"
            style={{ padding: 32, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 8 }}
          >
            <div
              style={{
                width: 100,
                height: 100,
                borderRadius: "50%",
                background: `conic-gradient(${overallColor} ${pct * 3.6}deg, rgba(255,255,255,0.05) 0deg)`,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                position: "relative",
              }}
            >
              <div
                style={{
                  width: 76,
                  height: 76,
                  borderRadius: "50%",
                  background: "var(--bg-primary)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  flexDirection: "column",
                }}
              >
                <span style={{ fontSize: 24, fontWeight: 800, color: overallColor }}>{summary.overall_score.toFixed(1)}</span>
                <span style={{ fontSize: 10, color: "var(--text-muted)" }}>/5.0</span>
              </div>
            </div>
            <span style={{ fontSize: 13, color: "var(--text-secondary)", textAlign: "center" }}>Overall Score</span>
          </div>

          {/* Strengths + gaps */}
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {/* Strengths */}
            <div className="glass-card" style={{ padding: 20, borderColor: "rgba(34,197,94,0.2)", flex: 1 }}>
              <h3
                style={{
                  color: "var(--color-score-strong)",
                  fontSize: 12,
                  fontWeight: 700,
                  textTransform: "uppercase",
                  letterSpacing: "0.08em",
                  marginBottom: 12,
                }}
              >
                ✓ Strengths
              </h3>
              <ul style={{ display: "flex", flexDirection: "column", gap: 8, margin: 0, padding: 0, listStyle: "none" }}>
                {summary.strengths.map((s, i) => (
                  <AnalysisCard key={i} item={s} variant="strength" />
                ))}
              </ul>
            </div>

            {/* Gaps */}
            <div className="glass-card" style={{ padding: 20, borderColor: "rgba(239,68,68,0.15)", flex: 1 }}>
              <h3
                style={{
                  color: "var(--color-score-weak)",
                  fontSize: 12,
                  fontWeight: 700,
                  textTransform: "uppercase",
                  letterSpacing: "0.08em",
                  marginBottom: 12,
                }}
              >
                ↗ Areas to Improve
              </h3>
              <ul style={{ display: "flex", flexDirection: "column", gap: 8, margin: 0, padding: 0, listStyle: "none" }}>
                {summary.gaps.map((g, i) => (
                  <AnalysisCard key={i} item={g} variant="gap" />
                ))}
              </ul>
            </div>
          </div>
        </div>

        {/* Transcript */}
        <h2 style={{ fontSize: 20, fontWeight: 700, marginBottom: 20, display: "flex", alignItems: "center", gap: 10 }}>
          Interview Transcript
          <span style={{ fontSize: 13, color: "var(--text-muted)", fontWeight: 400 }}>
            — expand &ldquo;Why this was asked&rdquo; to see source traceability
          </span>
        </h2>

        <div style={{ display: "flex", flexDirection: "column", gap: 16, marginBottom: 40 }}>
          {summary.transcript.map((item) => (
            <TranscriptCard key={item.order_index} item={item} />
          ))}
        </div>

        {/* CTA */}
        <div style={{ textAlign: "center" }}>
          <button className="btn-primary" onClick={() => router.push("/")} style={{ padding: "14px 40px" }}>
            Start New Interview
          </button>
        </div>
      </div>
    </main>
  );
}
