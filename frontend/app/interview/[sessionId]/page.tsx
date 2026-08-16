"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { api, QuestionOut, AnswerSubmitResponse } from "@/lib/api";

// Timer durations per difficulty (seconds)
const TIMER_SECONDS: Record<string, number> = {
  easy: 2 * 60,
  medium: 3 * 60,
  hard: 5 * 60,
};

function formatTime(secs: number): string {
  const m = Math.floor(secs / 60);
  const s = secs % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

function TimerBadge({ seconds, total }: { seconds: number; total: number }) {
  const pct = seconds / total;
  const cls =
    seconds <= 0
      ? "timer-expired"
      : pct <= 0.2
      ? "timer-warning"
      : "timer-normal";

  return (
    <div className={`timer-display ${cls}`}>
      <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
        <circle cx="12" cy="12" r="10" />
        <polyline points="12 6 12 12 16 14" />
      </svg>
      {seconds <= 0 ? "Time's up" : formatTime(seconds)}
    </div>
  );
}

export default function InterviewPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = Number(params.sessionId);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const [question, setQuestion] = useState<QuestionOut | null>(null);
  const [answer, setAnswer] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastEval, setLastEval] = useState<{ score: number; feedback: string } | null>(null);
  const [showEval, setShowEval] = useState(false);

  // Timer state
  const [timeLeft, setTimeLeft] = useState(0);
  const [totalTime, setTotalTime] = useState(0);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const startTimer = useCallback((difficulty: string) => {
    if (timerRef.current) clearInterval(timerRef.current);
    const duration = TIMER_SECONDS[difficulty] ?? TIMER_SECONDS.medium;
    setTimeLeft(duration);
    setTotalTime(duration);
    timerRef.current = setInterval(() => {
      setTimeLeft((prev) => {
        if (prev <= 1) {
          clearInterval(timerRef.current!);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  }, []);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  const loadQuestion = useCallback(async () => {
    try {
      const res = await api.getCurrentQuestion(sessionId);
      if (res.status === "completed") {
        router.replace(`/interview/${sessionId}/summary`);
        return;
      }
      setQuestion(res.question);
      if (res.question) startTimer(res.question.difficulty);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load question.");
    } finally {
      setLoading(false);
    }
  }, [sessionId, router, startTimer]);

  useEffect(() => { loadQuestion(); }, [loadQuestion]);

  useEffect(() => {
    if (question && textareaRef.current) textareaRef.current.focus();
  }, [question]);

  const handleSubmit = async () => {
    if (!answer.trim() || submitting) return;
    if (timerRef.current) clearInterval(timerRef.current);
    setSubmitting(true);
    setError(null);

    try {
      const res: AnswerSubmitResponse = await api.submitAnswer(sessionId, answer);
      setLastEval({ score: res.eval_score, feedback: res.eval_feedback });
      setShowEval(true);
      setAnswer("");

      if (res.status === "completed") {
        setTimeout(() => router.push(`/interview/${sessionId}/summary`), 2000);
        return;
      }

      setTimeout(() => {
        setShowEval(false);
        setQuestion(res.next_question);
        if (res.next_question) startTimer(res.next_question.difficulty);
        setSubmitting(false);
      }, 2000);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to submit answer.");
      setSubmitting(false);
      if (question) startTimer(question.difficulty); // resume timer on error
    }
  };

  const progress = question
    ? Math.round(((question.order_index - 1) / question.total_questions) * 100)
    : 0;

  const scoreRingClass = (s: number) =>
    s >= 4 ? "score-ring score-high" : s >= 3 ? "score-ring score-mid" : "score-ring score-low";

  if (loading) {
    return (
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", flexDirection: "column", gap: 16 }}>
        <div className="spinner" style={{ width: 40, height: 40 }} />
        <p style={{ color: "var(--text-secondary)" }}>Loading your interview…</p>
      </div>
    );
  }

  return (
    <main className="page-enter" style={{ minHeight: "100vh", padding: "24px 16px" }}>
      <div style={{ maxWidth: 760, margin: "0 auto" }}>

        {/* Top bar */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 32 }}>
          <span className="gradient-text" style={{ fontWeight: 800, fontSize: 20 }}>
            AI Screener
          </span>
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            {question && !showEval && (
              <TimerBadge seconds={timeLeft} total={totalTime} />
            )}
            {question && (
              <span style={{ color: "var(--text-secondary)", fontSize: 14 }}>
                Question {question.order_index} of {question.total_questions}
              </span>
            )}
          </div>
        </div>

        {/* Progress bar — teal accent */}
        {question && (
          <div style={{ marginBottom: 40 }}>
            <div className="progress-bar-track">
              <div className="progress-bar-fill" style={{ width: `${progress}%` }} />
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", marginTop: 8, fontSize: 12, color: "var(--text-muted)" }}>
              <span>{progress}% complete</span>
              <span>{question.total_questions - question.order_index + 1} questions remaining</span>
            </div>
          </div>
        )}

        {/* Time-up notice (non-blocking) */}
        {timeLeft === 0 && question && !showEval && !submitting && (
          <div
            className="page-enter"
            style={{
              background: "rgba(224,90,54,0.08)",
              border: "1px solid rgba(224,90,54,0.25)",
              borderRadius: 10,
              padding: "10px 16px",
              marginBottom: 16,
              fontSize: 13,
              color: "#E05A36",
              display: "flex",
              alignItems: "center",
              gap: 8,
            }}
          >
            ⏰ Time&apos;s up — feel free to still submit your answer, it won&apos;t affect your score.
          </div>
        )}

        {/* Eval flash */}
        {showEval && lastEval && (
          <div
            className="glass-card page-enter"
            style={{
              padding: "16px 20px",
              marginBottom: 24,
              borderColor: lastEval.score >= 4 ? "rgba(34,197,94,0.3)" : lastEval.score >= 3 ? "rgba(224,90,54,0.3)" : "rgba(239,68,68,0.3)",
              background: lastEval.score >= 4 ? "rgba(34,197,94,0.06)" : lastEval.score >= 3 ? "rgba(224,90,54,0.06)" : "rgba(239,68,68,0.06)",
              display: "flex",
              alignItems: "center",
              gap: 16,
            }}
          >
            <div className={scoreRingClass(lastEval.score)}>{lastEval.score}</div>
            <div>
              <div style={{ fontWeight: 600, marginBottom: 2 }}>Feedback</div>
              <div style={{ fontSize: 14, color: "var(--text-secondary)" }}>{lastEval.feedback}</div>
            </div>
          </div>
        )}

        {/* Question card */}
        {question && !showEval && (
          <div className="glass-card page-enter" style={{ padding: 36, marginBottom: 24 }}>
            {/* Meta */}
            <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 20 }}>
              <span className={`difficulty-badge difficulty-${question.difficulty}`}>
                {question.difficulty}
              </span>
              <span className="topic-pill">{question.topic}</span>
            </div>

            {/* Question text */}
            <p style={{ fontSize: 20, fontWeight: 600, lineHeight: 1.55, marginBottom: 28, color: "var(--text-primary)" }}>
              {question.text}
            </p>

            {/* Textarea */}
            <textarea
              ref={textareaRef}
              id="answer-input"
              className="answer-textarea"
              placeholder="Type your answer here… Be specific and explain your reasoning."
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) handleSubmit(); }}
              disabled={submitting}
            />

            {error && <p style={{ color: "var(--color-score-weak)", fontSize: 14, marginTop: 8 }}>{error}</p>}

            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: 20 }}>
              <span style={{ fontSize: 12, color: "var(--text-muted)" }}>Ctrl+Enter to submit</span>
              <button
                id="submit-answer-btn"
                className="btn-primary"
                style={{ minWidth: 160, padding: "12px 24px" }}
                disabled={!answer.trim() || submitting}
                onClick={handleSubmit}
              >
                {submitting ? (
                  <span style={{ display: "flex", alignItems: "center", gap: 8 }}>
                    <span className="spinner" />
                    Evaluating…
                  </span>
                ) : question.order_index === question.total_questions ? (
                  "Submit Final Answer →"
                ) : (
                  "Submit Answer →"
                )}
              </button>
            </div>
          </div>
        )}

        {/* Tips */}
        {question && !showEval && (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
            {[
              { icon: "🎯", label: "Be specific", desc: "Use concrete examples" },
              { icon: "📐", label: "Show reasoning", desc: "Explain your thought process" },
              { icon: "⚡", label: "Adaptive", desc: "Difficulty adjusts to your answers" },
            ].map((tip) => (
              <div
                key={tip.label}
                style={{
                  background: "var(--bg-surface)",
                  border: "1px solid rgba(168,162,158,0.15)",
                  borderRadius: 10,
                  padding: "12px 14px",
                  textAlign: "center",
                }}
              >
                <div style={{ fontSize: 20, marginBottom: 4 }}>{tip.icon}</div>
                <div style={{ fontSize: 12, fontWeight: 600, marginBottom: 2 }}>{tip.label}</div>
                <div style={{ fontSize: 11, color: "var(--text-muted)" }}>{tip.desc}</div>
              </div>
            ))}
          </div>
        )}
      </div>
    </main>
  );
}
