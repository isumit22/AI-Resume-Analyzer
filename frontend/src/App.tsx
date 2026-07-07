import { FormEvent, useEffect, useMemo, useState } from 'react';

type SectionFeedback = {
  title: string;
  items: string[];
};

type AnalysisResponse = {
  analysis_id: string | null;
  created_at: string | null;
  resume_filename: string;
  job_description_filename: string;
  ats_score: number;
  matched_keywords: string[];
  missing_keywords: string[];
  retrieved_context: string[];
  agent_trace: string[];
  strengths: SectionFeedback;
  weaknesses: SectionFeedback;
  suggestions: SectionFeedback;
  interview_questions: SectionFeedback;
  learning_roadmap: SectionFeedback;
  recruiter_feedback: string;
};

type AnalysisSummary = {
  analysis_id: string;
  created_at: string;
  resume_filename: string;
  job_description_filename: string;
  ats_score: number;
  matched_count: number;
  missing_count: number;
};

type AuthResponse = {
  access_token: string;
  token_type: string;
  username: string;
};

type CurrentUserResponse = {
  username: string;
};

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';
const TOKEN_STORAGE_KEY = 'ai_resume_analyzer_token';
const USER_STORAGE_KEY = 'ai_resume_analyzer_username';

function SectionCard({ title, items }: SectionFeedback) {
  return (
    <section className="rounded-3xl border border-white/10 bg-white/8 p-5 shadow-soft backdrop-blur-xl">
      <h3 className="text-sm font-semibold uppercase tracking-[0.25em] text-cyan-200/90">{title}</h3>
      <ul className="mt-4 space-y-3 text-sm text-slate-100/90">
        {items.map((item) => (
          <li key={item} className="rounded-2xl border border-white/10 bg-slate-950/30 px-4 py-3">
            {item}
          </li>
        ))}
      </ul>
    </section>
  );
}

function MetricPill({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-slate-950/30 px-4 py-3 shadow-soft">
      <p className="text-[11px] uppercase tracking-[0.3em] text-slate-400">{label}</p>
      <p className="mt-1 text-lg font-semibold text-white">{value}</p>
    </div>
  );
}

function App() {
  const storedToken = useMemo(() => localStorage.getItem(TOKEN_STORAGE_KEY), []);
  const storedUsername = useMemo(() => localStorage.getItem(USER_STORAGE_KEY), []);
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [jdFile, setJdFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [result, setResult] = useState<AnalysisResponse | null>(null);
  const [history, setHistory] = useState<AnalysisSummary[]>([]);
  const [authToken, setAuthToken] = useState<string | null>(storedToken);
  const [username, setUsername] = useState<string>(storedUsername ?? '');
  const [password, setPassword] = useState('');
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState('');

  async function fetchWithAuth(input: RequestInfo | URL, init: RequestInit = {}) {
    const headers = new Headers(init.headers);
    if (authToken) {
      headers.set('Authorization', `Bearer ${authToken}`);
    }

    return fetch(input, { ...init, headers });
  }

  async function loadHistory() {
    if (!authToken) {
      setHistory([]);
      return;
    }

    try {
      const response = await fetchWithAuth(`${API_URL}/api/analyses?limit=6`);
      if (!response.ok) {
        return;
      }

      const data = (await response.json()) as AnalysisSummary[];
      setHistory(data);
    } catch {
      setHistory([]);
    }
  }

  useEffect(() => {
    void loadHistory();
  }, [authToken]);

  useEffect(() => {
    if (!authToken) {
      return;
    }

    fetchWithAuth(`${API_URL}/api/auth/me`).then(async (response) => {
      if (!response.ok) {
        return;
      }

      const data = (await response.json()) as CurrentUserResponse;
      setUsername(data.username);
      localStorage.setItem(USER_STORAGE_KEY, data.username);
    });
  }, [authToken]);

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!username.trim() || !password.trim()) {
      setAuthError('Enter a username and password.');
      return;
    }

    setAuthLoading(true);
    setAuthError('');

    try {
      const response = await fetch(`${API_URL}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });

      if (!response.ok) {
        throw new Error('Login failed.');
      }

      const data = (await response.json()) as AuthResponse;
      setAuthToken(data.access_token);
      localStorage.setItem(TOKEN_STORAGE_KEY, data.access_token);
      localStorage.setItem(USER_STORAGE_KEY, data.username);
      setUsername(data.username);
      setPassword('');
    } catch (loginError) {
      setAuthError(loginError instanceof Error ? loginError.message : 'Unable to sign in.');
    } finally {
      setAuthLoading(false);
    }
  }

  function handleLogout() {
    setAuthToken(null);
    setHistory([]);
    setResult(null);
    localStorage.removeItem(TOKEN_STORAGE_KEY);
    localStorage.removeItem(USER_STORAGE_KEY);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    if (!resumeFile || !jdFile) {
      setError('Upload both a resume PDF and a job description PDF.');
      return;
    }

    setError('');
    setLoading(true);
    setResult(null);

    try {
      const formData = new FormData();
      formData.append('resume', resumeFile);
      formData.append('job_description', jdFile);

      const response = await fetchWithAuth(`${API_URL}/api/analyze`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        if (response.status === 401) {
          throw new Error('Please sign in before running an analysis.');
        }

        throw new Error('Analysis request failed.');
      }

      const data = (await response.json()) as AnalysisResponse;
      setResult(data);
      void loadHistory();
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Unable to analyze the files.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen overflow-hidden bg-[radial-gradient(circle_at_top_left,_rgba(34,211,238,0.2),_transparent_34%),radial-gradient(circle_at_85%_10%,_rgba(16,185,129,0.18),_transparent_28%),linear-gradient(135deg,_#020617_0%,_#0f172a_48%,_#111827_100%)] text-white">
      <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[size:72px_72px] opacity-30" />
      <div className="relative mx-auto flex max-w-7xl flex-col gap-10 px-4 py-8 sm:px-6 lg:px-8">
        <header className="grid gap-6 lg:grid-cols-[1.3fr_0.7fr] lg:items-end">
          <div className="space-y-5">
            <div className="inline-flex items-center gap-2 rounded-full border border-cyan-400/30 bg-cyan-400/10 px-4 py-2 text-xs uppercase tracking-[0.35em] text-cyan-100">
              AI Resume Analyzer MVP
            </div>
            <h1 className="max-w-4xl text-4xl font-black tracking-tight text-white sm:text-6xl">
              Compare a resume to a job description and surface the exact gaps that matter.
            </h1>
            <p className="max-w-3xl text-base leading-7 text-slate-300 sm:text-lg">
              Upload two PDFs, extract the text, run ATS keyword analysis, and generate a recruiter-style
              review, roadmap, and interview prep. Gemini is used when configured; otherwise the app falls back
              to local analysis.
            </p>
          </div>

          <div className="grid gap-3 rounded-[2rem] border border-white/10 bg-white/5 p-5 shadow-soft backdrop-blur-xl">
            <MetricPill label="Pipeline" value="PDF -> retrieval -> analysis" />
            <MetricPill label="Core Stack" value="FastAPI + React + Tailwind" />
            <MetricPill label="Vector Store" value="FAISS first, Chroma next" />
          </div>
        </header>

        <section className="grid gap-6 lg:grid-cols-[0.88fr_1.12fr]">
          <form
            onSubmit={handleLogin}
            className="rounded-[2rem] border border-white/10 bg-slate-950/40 p-6 shadow-soft backdrop-blur-xl"
          >
            <h2 className="text-xl font-semibold text-white">Sign in to save history</h2>
            <p className="mt-2 text-sm leading-6 text-slate-300">
              This is a local MVP login. It creates your account on first sign in and keeps your analysis history private by username.
            </p>

            <div className="mt-6 space-y-4">
              <label className="block">
                <span className="text-sm font-medium text-cyan-100">Username</span>
                <input
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                  className="mt-2 w-full rounded-2xl border border-white/10 bg-slate-950/40 px-4 py-3 text-white outline-none ring-0 placeholder:text-slate-500 focus:border-cyan-300"
                  placeholder="your name or email"
                />
              </label>

              <label className="block">
                <span className="text-sm font-medium text-cyan-100">Password</span>
                <input
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  className="mt-2 w-full rounded-2xl border border-white/10 bg-slate-950/40 px-4 py-3 text-white outline-none ring-0 placeholder:text-slate-500 focus:border-cyan-300"
                  placeholder="choose a private password"
                />
              </label>
            </div>

            {authError ? (
              <p className="mt-4 rounded-2xl border border-rose-400/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
                {authError}
              </p>
            ) : null}

            <button
              type="submit"
              disabled={authLoading}
              className="mt-6 inline-flex w-full items-center justify-center rounded-2xl bg-white px-5 py-3 text-sm font-semibold text-slate-950 transition hover:scale-[1.01] disabled:cursor-not-allowed disabled:opacity-70"
            >
              {authLoading ? 'Signing in...' : authToken ? 'Switch account' : 'Sign in / create account'}
            </button>

            {authToken ? (
              <button
                type="button"
                onClick={handleLogout}
                className="mt-3 inline-flex w-full items-center justify-center rounded-2xl border border-white/10 bg-white/5 px-5 py-3 text-sm font-semibold text-white transition hover:bg-white/10"
              >
                Log out
              </button>
            ) : null}
          </form>

          <div className="rounded-[2rem] border border-white/10 bg-white/5 p-6 shadow-soft backdrop-blur-xl">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div>
                <p className="text-sm uppercase tracking-[0.25em] text-slate-400">Current session</p>
                <h2 className="mt-2 text-xl font-semibold text-white">{authToken ? `Signed in as ${username}` : 'Not signed in'}</h2>
              </div>
              <div className="rounded-3xl border border-white/10 bg-slate-950/40 px-4 py-3 text-right">
                <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Saved runs</p>
                <p className="mt-1 text-3xl font-black text-cyan-300">{history.length}</p>
              </div>
            </div>

            <div className="mt-6 grid gap-4 sm:grid-cols-3">
              <MetricPill label="Private history" value={authToken ? 'Enabled' : 'Locked'} />
              <MetricPill label="Login" value={authToken ? 'Ready' : 'Required'} />
              <MetricPill label="Sharing" value="Local MVP only" />
            </div>
          </div>
        </section>

        <section className="grid gap-6 lg:grid-cols-[0.92fr_1.08fr]">
          <form
            onSubmit={handleSubmit}
            className="rounded-[2rem] border border-white/10 bg-slate-950/40 p-6 shadow-soft backdrop-blur-xl"
          >
            <h2 className="text-xl font-semibold text-white">Step 1. Upload your files</h2>
            <p className="mt-2 text-sm leading-6 text-slate-300">
              The backend extracts PDF text, then you can layer chunking, embeddings, vector search, and LLM analysis on top.
            </p>

            <div className="mt-6 space-y-4">
              <label className="block rounded-3xl border border-dashed border-cyan-300/30 bg-white/5 p-5">
                <span className="text-sm font-medium text-cyan-100">Resume PDF</span>
                <input
                  type="file"
                  accept="application/pdf"
                  className="mt-3 block w-full text-sm text-slate-300 file:mr-4 file:rounded-full file:border-0 file:bg-cyan-400 file:px-4 file:py-2 file:text-sm file:font-semibold file:text-slate-950 hover:file:bg-cyan-300"
                  onChange={(event) => setResumeFile(event.target.files?.[0] ?? null)}
                />
                <p className="mt-2 text-xs text-slate-400">Selected: {resumeFile?.name ?? 'No file chosen'}</p>
              </label>

              <label className="block rounded-3xl border border-dashed border-emerald-300/30 bg-white/5 p-5">
                <span className="text-sm font-medium text-emerald-100">Job Description PDF</span>
                <input
                  type="file"
                  accept="application/pdf"
                  className="mt-3 block w-full text-sm text-slate-300 file:mr-4 file:rounded-full file:border-0 file:bg-emerald-400 file:px-4 file:py-2 file:text-sm file:font-semibold file:text-slate-950 hover:file:bg-emerald-300"
                  onChange={(event) => setJdFile(event.target.files?.[0] ?? null)}
                />
                <p className="mt-2 text-xs text-slate-400">Selected: {jdFile?.name ?? 'No file chosen'}</p>
              </label>
            </div>

            {error ? (
              <p className="mt-4 rounded-2xl border border-rose-400/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-100">
                {error}
              </p>
            ) : null}

            <button
              type="submit"
              disabled={loading}
              className="mt-6 inline-flex w-full items-center justify-center rounded-2xl bg-white px-5 py-3 text-sm font-semibold text-slate-950 transition hover:scale-[1.01] disabled:cursor-not-allowed disabled:opacity-70"
            >
              {loading ? 'Analyzing resume...' : 'Run analysis'}
            </button>
          </form>

          <div className="space-y-6">
            <section className="rounded-[2rem] border border-white/10 bg-white/5 p-6 shadow-soft backdrop-blur-xl">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <h2 className="text-xl font-semibold text-white">Results dashboard</h2>
                  <p className="mt-1 text-sm text-slate-300">
                    ATS score, missing keywords, strengths, weaknesses, and the next actions.
                  </p>
                </div>
                <div className="rounded-3xl border border-white/10 bg-slate-950/40 px-4 py-3 text-right">
                  <p className="text-xs uppercase tracking-[0.3em] text-slate-400">Match score</p>
                  <p className="mt-1 text-3xl font-black text-cyan-300">
                    {result ? `${result.ats_score}%` : '--'}
                  </p>
                </div>
              </div>

              <div className="mt-6 grid gap-4 sm:grid-cols-3">
                <MetricPill label="Matched" value={result ? String(result.matched_keywords.length) : '--'} />
                <MetricPill label="Missing" value={result ? String(result.missing_keywords.length) : '--'} />
                <MetricPill label="Stage" value={loading ? 'Analyzing' : 'Ready'} />
              </div>

              <div className="mt-6 rounded-3xl border border-white/10 bg-slate-950/30 p-5">
                <p className="text-sm font-semibold uppercase tracking-[0.25em] text-cyan-100">Recruiter feedback</p>
                <p className="mt-3 text-sm leading-7 text-slate-200">
                  {result
                    ? result.recruiter_feedback
                    : 'Upload both PDFs to get a baseline score and a recruiter-style breakdown.'}
                </p>
              </div>

              {result ? (
                <div className="mt-6 rounded-3xl border border-white/10 bg-slate-950/30 p-5">
                  <p className="text-sm font-semibold uppercase tracking-[0.25em] text-emerald-100">Agent trace</p>
                  <ol className="mt-4 space-y-3 text-sm text-slate-200">
                    {result.agent_trace.map((step, index) => (
                      <li key={step} className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
                        {index + 1}. {step}
                      </li>
                    ))}
                  </ol>
                </div>
              ) : null}
            </section>

            {result ? (
              <section className="grid gap-4 md:grid-cols-2">
                <SectionCard {...result.strengths} />
                <SectionCard {...result.weaknesses} />
                <SectionCard {...result.suggestions} />
                <SectionCard {...result.interview_questions} />
                <div className="md:col-span-2 rounded-3xl border border-emerald-300/20 bg-emerald-400/10 p-5 shadow-soft backdrop-blur-xl">
                  <h3 className="text-sm font-semibold uppercase tracking-[0.25em] text-emerald-100">Learning roadmap</h3>
                  <div className="mt-4 flex flex-wrap gap-3 text-sm text-emerald-50">
                    {result.learning_roadmap.items.map((item, index) => (
                      <div
                        key={item}
                        className="rounded-full border border-emerald-200/20 bg-slate-950/30 px-4 py-2"
                      >
                        {index + 1}. {item}
                      </div>
                    ))}
                  </div>
                </div>
                <div className="md:col-span-2 rounded-3xl border border-cyan-300/20 bg-cyan-400/10 p-5 shadow-soft backdrop-blur-xl">
                  <h3 className="text-sm font-semibold uppercase tracking-[0.25em] text-cyan-100">Retrieved context</h3>
                  <div className="mt-4 grid gap-3">
                    {result.retrieved_context.map((item) => (
                      <div key={item} className="rounded-2xl border border-white/10 bg-slate-950/30 px-4 py-3 text-sm text-slate-100">
                        {item}
                      </div>
                    ))}
                  </div>
                </div>
              </section>
            ) : (
              <section className="grid gap-4 md:grid-cols-2">
                <div className="rounded-3xl border border-white/10 bg-white/5 p-5 text-sm leading-7 text-slate-300">
                  The first milestone is a working upload and text extraction loop. The next milestone is the RAG layer.
                </div>
                <div className="rounded-3xl border border-white/10 bg-white/5 p-5 text-sm leading-7 text-slate-300">
                  After that, plug in embeddings, FAISS, a recruiter prompt, and a structured agent pipeline.
                </div>
              </section>
            )}

            <section className="rounded-[2rem] border border-white/10 bg-white/5 p-6 shadow-soft backdrop-blur-xl">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <h2 className="text-xl font-semibold text-white">Recent analyses</h2>
                  <p className="mt-1 text-sm text-slate-300">
                    Saved runs from the local history store.
                  </p>
                </div>
                <p className="text-sm text-slate-400">{history.length} saved</p>
              </div>

              <div className="mt-4 grid gap-3">
                {history.length > 0 ? (
                  history.map((item) => (
                    <div key={item.analysis_id} className="rounded-3xl border border-white/10 bg-slate-950/30 px-4 py-4">
                      <div className="flex flex-wrap items-center justify-between gap-3">
                        <div>
                          <p className="text-sm font-semibold text-white">{item.resume_filename}</p>
                          <p className="text-xs text-slate-400">{item.job_description_filename}</p>
                        </div>
                        <div className="text-right">
                          <p className="text-lg font-bold text-cyan-300">{item.ats_score}%</p>
                          <p className="text-xs text-slate-400">
                            {item.matched_count} matched / {item.missing_count} missing
                          </p>
                        </div>
                      </div>
                      <p className="mt-3 text-xs text-slate-500">{item.created_at}</p>
                    </div>
                  ))
                ) : (
                  <p className="rounded-3xl border border-dashed border-white/10 bg-slate-950/20 px-4 py-6 text-sm text-slate-400">
                    No saved analyses yet. Run one analysis to create your first history record.
                  </p>
                )}
              </div>
            </section>
          </div>
        </section>
      </div>
    </main>
  );
}

export default App;
