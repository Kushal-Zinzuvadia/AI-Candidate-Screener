const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Role {
  id: number;
  name: string;
  description: string;
  kb_ready: boolean;
}

export interface QuestionOut {
  id: number;
  text: string;
  topic: string;
  difficulty: "easy" | "medium" | "hard";
  order_index: number;
  total_questions: number;
}

export interface ResumeParsedResponse {
  resume_id: number;
  candidate_id: number;
  parsed_skills: string[];
  parsed_technologies: string[];
  profile_summary: string;
}

export interface InterviewStartResponse {
  session_id: number;
  status: string;
  question: QuestionOut;
}

export interface CurrentQuestionResponse {
  session_id: number;
  status: string;
  question: QuestionOut | null;
}

export interface AnswerSubmitResponse {
  eval_score: number;
  eval_feedback: string;
  next_question: QuestionOut | null;
  status: string;
}

export interface TranscriptItem {
  order_index: number;
  question: string;
  topic: string;
  difficulty: string;
  answer: string;
  score: number;
  feedback: string;
  source_chunk_ids: string[];
  rationale?: string;
}

export interface StrengthGapItem {
  area: string;
  detail: string;
}

export interface SummaryResponse {
  session_id: number;
  overall_score: number;
  strengths: StrengthGapItem[];
  gaps: StrengthGapItem[];
  summary_text: string;
  transcript: TranscriptItem[];
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", "ngrok-skip-browser-warning": "true" },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

export const api = {
  getRoles: () => request<Role[]>("/api/roles"),

  uploadResume: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return fetch(`${API_BASE}/api/resumes/upload`, { method: "POST", body: form })
      .then(async (res) => {
        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: res.statusText }));
          throw new Error(err.detail || `Upload failed: ${res.status}`);
        }
        return res.json() as Promise<ResumeParsedResponse>;
      });
  },

  startInterview: (resume_id: number, role_id: number) =>
    request<InterviewStartResponse>("/api/interviews", {
      method: "POST",
      body: JSON.stringify({ resume_id, role_id }),
    }),

  getCurrentQuestion: (sessionId: number) =>
    request<CurrentQuestionResponse>(`/api/interviews/${sessionId}/current-question`),

  submitAnswer: (sessionId: number, answer_text: string) =>
    request<AnswerSubmitResponse>(`/api/interviews/${sessionId}/answer`, {
      method: "POST",
      body: JSON.stringify({ answer_text }),
    }),

  getSummary: (sessionId: number) =>
    request<SummaryResponse>(`/api/interviews/${sessionId}/summary`),
};
