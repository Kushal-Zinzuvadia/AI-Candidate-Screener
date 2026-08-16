"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { api, Role, ResumeParsedResponse } from "@/lib/api";

type Step = "upload" | "parsed" | "ready";

export default function HomePage() {
  const router = useRouter();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [step, setStep] = useState<Step>("upload");
  const [dragging, setDragging] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [parsed, setParsed] = useState<ResumeParsedResponse | null>(null);
  const [roles, setRoles] = useState<Role[]>([]);
  const [selectedRole, setSelectedRole] = useState<number | null>(null);
  const [uploading, setUploading] = useState(false);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getRoles().then(setRoles).catch(() => {});
  }, []);

  const handleFile = useCallback(
    async (f: File) => {
      if (!f.name.endsWith(".pdf")) {
        setError("Only PDF files are supported.");
        return;
      }
      setFile(f);
      setError(null);
      setUploading(true);
      try {
        const result = await api.uploadResume(f);
        setParsed(result);
        setStep("parsed");
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Upload failed.");
      } finally {
        setUploading(false);
      }
    },
    []
  );

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragging(false);
      const f = e.dataTransfer.files[0];
      if (f) handleFile(f);
    },
    [handleFile]
  );

  const startInterview = async () => {
    if (!parsed || !selectedRole) return;
    setStarting(true);
    setError(null);
    try {
      const session = await api.startInterview(parsed.resume_id, selectedRole);
      router.push(`/interview/${session.session_id}`);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to start interview.");
      setStarting(false);
    }
  };

  return (
    <main className="page-enter min-h-screen flex flex-col items-center justify-center px-4 py-16">
      {/* Header */}
      <div className="text-center mb-12 max-w-2xl">
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
          }}
        >
          <span style={{ fontSize: 14, color: "#FDBA8C" }}>
            ✦ AI-Powered Technical Screening
          </span>
        </div>
        <h1
          className="gradient-text"
          style={{ fontSize: 48, fontWeight: 800, lineHeight: 1.1, marginBottom: 16 }}
        >
          Candidate Screener
        </h1>
        <p style={{ color: "var(--text-secondary)", fontSize: 18, lineHeight: 1.6 }}>
          Upload your resume, select a role, and experience an adaptive technical
          interview grounded in a curated knowledge base.
        </p>
      </div>

      {/* Card */}
      <div className="glass-card" style={{ width: "100%", maxWidth: 600, padding: 40 }}>
        {/* Step 1: Upload */}
        {step === "upload" && (
          <div>
            <h2 style={{ fontSize: 22, fontWeight: 700, marginBottom: 8 }}>
              Upload Your Resume
            </h2>
            <p style={{ color: "var(--text-secondary)", fontSize: 14, marginBottom: 24 }}>
              PDF format, up to 10MB. We&apos;ll extract your skills automatically.
            </p>

            <div
              id="drop-zone"
              className={`drop-zone ${dragging ? "dragging" : ""}`}
              onClick={() => fileInputRef.current?.click()}
              onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
              onDragLeave={() => setDragging(false)}
              onDrop={onDrop}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf"
                style={{ display: "none" }}
                onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
              />
              {uploading ? (
                <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 12 }}>
                  <div className="spinner" style={{ width: 36, height: 36 }} />
                  <p style={{ color: "var(--text-secondary)" }}>Parsing resume…</p>
                </div>
              ) : (
                <>
                  <div style={{ fontSize: 40, marginBottom: 12 }}>📄</div>
                  <p style={{ fontWeight: 600, marginBottom: 6 }}>
                    {file ? file.name : "Drop your PDF here"}
                  </p>
                  <p style={{ color: "var(--text-muted)", fontSize: 13 }}>
                    or click to browse
                  </p>
                </>
              )}
            </div>

            {error && (
              <p style={{ color: "#f87171", fontSize: 14, marginTop: 12 }}>{error}</p>
            )}
          </div>
        )}

        {/* Step 2: Parsed + role select */}
        {step === "parsed" && parsed && (
          <div className="page-enter">
            {/* Parsed summary */}
            <div
              style={{
                background: "rgba(74,222,128,0.07)",
                border: "1px solid rgba(74,222,128,0.2)",
                borderRadius: 12,
                padding: 16,
                marginBottom: 28,
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 12 }}>
                <span style={{ color: "#4ADE80", fontSize: 16 }}>✓</span>
                <span style={{ fontWeight: 600, color: "#4ADE80" }}>Resume parsed successfully</span>
              </div>
              <p style={{ fontSize: 13, color: "var(--text-secondary)", marginBottom: 12, lineHeight: 1.6 }}>
                {parsed.profile_summary}
              </p>
              {parsed.parsed_skills.length > 0 && (
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {[...parsed.parsed_skills, ...parsed.parsed_technologies].slice(0, 12).map((s) => (
                    <span
                      key={s}
                      className="topic-pill"
                    >
                      {s}
                    </span>
                  ))}
                </div>
              )}
            </div>

            {/* Role selection */}
            <h2 style={{ fontSize: 18, fontWeight: 700, marginBottom: 6 }}>
              Select a Role
            </h2>
            <p style={{ color: "var(--text-secondary)", fontSize: 14, marginBottom: 16 }}>
              Choose the position you&apos;re being screened for.
            </p>

            <div style={{ display: "flex", flexDirection: "column", gap: 10, marginBottom: 28 }}>
              {roles.map((role) => (
                <button
                  key={role.id}
                  onClick={() => setSelectedRole(role.id)}
                  disabled={!role.kb_ready}
                  style={{
                    background:
                      selectedRole === role.id
                        ? "rgba(224,90,54,0.12)"
                        : "var(--bg-surface)",
                    border: `1px solid ${selectedRole === role.id ? "rgba(224,90,54,0.5)" : "rgba(168,162,158,0.18)"}`,
                    borderRadius: 12,
                    padding: "14px 18px",
                    textAlign: "left",
                    cursor: role.kb_ready ? "pointer" : "not-allowed",
                    transition: "all 0.15s ease",
                    opacity: role.kb_ready ? 1 : 0.45,
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <div>
                      <div style={{ fontWeight: 600, marginBottom: 4 }}>{role.name}</div>
                      <div style={{ fontSize: 13, color: "var(--text-secondary)" }}>
                        {role.description}
                      </div>
                    </div>
                    {!role.kb_ready && (
                      <span style={{ fontSize: 11, color: "var(--text-muted)", whiteSpace: "nowrap", marginLeft: 12 }}>
                        KB not ingested
                      </span>
                    )}
                    {selectedRole === role.id && (
                      <span style={{ color: "#4ADE80", fontSize: 18 }}>✓</span>
                    )}
                  </div>
                </button>
              ))}
            </div>

            {error && (
              <p style={{ color: "#f87171", fontSize: 14, marginBottom: 16 }}>{error}</p>
            )}

            <button
              id="start-interview-btn"
              className="btn-primary"
              style={{ width: "100%", padding: 16 }}
              disabled={!selectedRole || starting}
              onClick={startInterview}
            >
              {starting ? (
                <span style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 10 }}>
                  <span className="spinner" />
                  Generating first question…
                </span>
              ) : (
                "Start Interview →"
              )}
            </button>

            <button
              style={{
                marginTop: 12,
                width: "100%",
                background: "transparent",
                border: "none",
                color: "var(--text-muted)",
                cursor: "pointer",
                fontSize: 14,
                padding: 8,
              }}
              onClick={() => { setStep("upload"); setFile(null); setParsed(null); setSelectedRole(null); }}
            >
              ← Upload a different resume
            </button>
          </div>
        )}
      </div>

      {/* Footer */}
      <p style={{ marginTop: 40, color: "var(--text-muted)", fontSize: 13 }}>
        AI/ML & Backend Engineering roles available · Adaptive difficulty · Grounded in knowledge bases
      </p>
    </main>
  );
}
