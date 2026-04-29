"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import {
  AlertCircle,
  ArrowLeft,
  Briefcase,
  ClipboardList,
  Loader2,
  MessageSquareText,
  Sparkles,
  Trophy,
  UploadCloud,
  Video,
} from "lucide-react"
import Link from "next/link"
import { ApiBackendBanner } from "@/components/api-backend-banner"
import { InterviewLiveCapture } from "@/components/interview-live-capture"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Spinner } from "@/components/ui/spinner"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"

type QuestionDTO = {
  id: string
  order_index: number
  question_text: string
  skill_target: string
  difficulty: string
}

type EvaluationDTO = {
  question_id: string
  rubric_id: string
  scores: Record<string, unknown>
  explanation: string
  model_id: string
}

type ResultsPayload = {
  session_id: string
  status: string
  evaluations: EvaluationDTO[]
  interview_average: number | null
  hire_decision?: string | null
  hire_rationale?: string | null
  aggregated: {
    resume: number | null
    test: number | null
    interview: number | null
    combined: number | null
    weights: Record<string, number>
  }
}

const SAMPLE_JD = `Senior Backend Engineer

We need someone to own APIs, data, and reliability.

Requirements:
- Python (FastAPI or Django), PostgreSQL, Redis
- Production debugging, metrics, on-call experience
- Clear written and verbal communication

Nice to have: LangChain / async workers / event-driven design.`

const LIVE_RECORD_SECONDS = 30

async function readError(res: Response): Promise<string> {
  let detail = `Request failed (${res.status})`
  try {
    const data = await res.json()
    if (typeof data?.detail === "string") detail = data.detail
    else if (Array.isArray(data?.detail)) detail = data.detail.map((d: { msg?: string }) => d.msg).join("; ")
  } catch {
    // ignore
  }
  return detail
}

export function InterviewTool() {
  const [jobDescription, setJobDescription] = useState(SAMPLE_JD)
  const [skillsRaw, setSkillsRaw] = useState("Python, PostgreSQL, Redis")
  const [resumeScore, setResumeScore] = useState<string>("")
  const [testScore, setTestScore] = useState<string>("")
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [currentQuestion, setCurrentQuestion] = useState<QuestionDTO | null>(null)
  const [answerTab, setAnswerTab] = useState<"text" | "audio" | "live">("live")
  const [transcript, setTranscript] = useState("")
  const [audioFile, setAudioFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [phase, setPhase] = useState<"setup" | "live" | "done">("setup")
  const [error, setError] = useState<string | null>(null)
  const [results, setResults] = useState<ResultsPayload | null>(null)
  const [totalQuestions, setTotalQuestions] = useState(5)

  useEffect(() => {
    const raw = typeof window !== "undefined" ? sessionStorage.getItem("fh_interview_prefill") : null
    if (!raw) return
    try {
      const p = JSON.parse(raw) as {
        jobDescription?: string
        skills?: string[]
        resumeScore?: number
      }
      if (typeof p.jobDescription === "string" && p.jobDescription.trim()) {
        setJobDescription(p.jobDescription)
      }
      if (Array.isArray(p.skills) && p.skills.length > 0) {
        setSkillsRaw(p.skills.join(", "))
      }
      if (typeof p.resumeScore === "number" && Number.isFinite(p.resumeScore)) {
        setResumeScore(String(Math.round(p.resumeScore)))
      }
    } catch {
      // ignore malformed storage
    } finally {
      sessionStorage.removeItem("fh_interview_prefill")
    }
  }, [])

  const skillsList = useMemo(
    () =>
      skillsRaw
        .split(/[,;\n]+/)
        .map((s) => s.trim())
        .filter(Boolean),
    [skillsRaw],
  )

  const resetFlow = useCallback(() => {
    setSessionId(null)
    setCurrentQuestion(null)
    setTranscript("")
    setAudioFile(null)
    setAnswerTab("live")
    setPhase("setup")
    setError(null)
    setResults(null)
    setTotalQuestions(5)
  }, [])

  const startInterview = useCallback(async () => {
    setError(null)
    if (!jobDescription.trim()) {
      setError("Add a job description.")
      return
    }
    setLoading(true)
    try {
      const body: Record<string, unknown> = {
        job_description: jobDescription.trim(),
        skills: skillsList,
      }
      const rs = resumeScore.trim() ? Number(resumeScore) : undefined
      const ts = testScore.trim() ? Number(testScore) : undefined
      if (resumeScore.trim() && !Number.isFinite(rs)) throw new Error("Resume score must be a number 0–100.")
      if (testScore.trim() && !Number.isFinite(ts)) throw new Error("Test score must be a number 0–100.")
      if (rs !== undefined) body.resume_score = rs
      if (ts !== undefined) body.test_score = ts

      const res = await fetch("/api/interview/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      })
      if (!res.ok) throw new Error(await readError(res))
      const data = (await res.json()) as {
        id: string
        first_question: QuestionDTO | null
        total_questions?: number
      }
      setSessionId(data.id)
      setCurrentQuestion(data.first_question)
      setTotalQuestions(typeof data.total_questions === "number" ? data.total_questions : 5)
      setPhase("live")
      setAnswerTab("live")

      const jr = await fetch(`/api/interview/${data.id}/join`, { method: "POST" })
      if (!jr.ok) throw new Error(await readError(jr))
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not start interview.")
    } finally {
      setLoading(false)
    }
  }, [jobDescription, resumeScore, skillsList, testScore])

  const refreshQuestion = useCallback(async (sid: string) => {
    const res = await fetch(`/api/interview/${sid}/next-question`, { method: "POST" })
    if (!res.ok) throw new Error(await readError(res))
    const data = (await res.json()) as { interview_complete: boolean; question: QuestionDTO | null }
    if (data.interview_complete || !data.question) {
      setCurrentQuestion(null)
      return false
    }
    setCurrentQuestion(data.question)
    return true
  }, [])

  const submitAnswerWithFile = useCallback(
    async (file: File) => {
      if (!sessionId || !currentQuestion) return
      const qid = currentQuestion.id
      setError(null)
      setLoading(true)
      try {
        const fd = new FormData()
        fd.append("question_id", qid)
        fd.append("audio", file)
        const res = await fetch(`/api/interview/${sessionId}/submit-audio`, {
          method: "POST",
          body: fd,
        })
        if (!res.ok) throw new Error(await readError(res))
        const meta = (await res.json()) as { interview_complete?: boolean }
        setTranscript("")
        setAudioFile(null)

        if (meta.interview_complete) {
          setPhase("done")
          setCurrentQuestion(null)
          const rr = await fetch(`/api/interview/${sessionId}/results`)
          if (!rr.ok) throw new Error(await readError(rr))
          setResults((await rr.json()) as ResultsPayload)
        } else {
          const hasNext = await refreshQuestion(sessionId)
          if (!hasNext) {
            setPhase("done")
            const rr = await fetch(`/api/interview/${sessionId}/results`)
            if (rr.ok) setResults((await rr.json()) as ResultsPayload)
          }
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : "Submit failed.")
      } finally {
        setLoading(false)
      }
    },
    [currentQuestion, refreshQuestion, sessionId],
  )

  const submitAnswer = useCallback(async () => {
    if (!sessionId || !currentQuestion) return
    setError(null)
    if (!transcript.trim() && !audioFile) {
      setError("Add a typed answer, upload a file, or use the Live camera tab (30s auto-submit per question).")
      return
    }
    setLoading(true)
    try {
      const fd = new FormData()
      fd.append("question_id", currentQuestion.id)
      if (transcript.trim()) {
        fd.append("transcript", transcript.trim())
      } else if (audioFile) {
        fd.append("audio", audioFile)
      }

      const res = await fetch(`/api/interview/${sessionId}/submit-audio`, {
        method: "POST",
        body: fd,
      })
      if (!res.ok) throw new Error(await readError(res))
      const meta = (await res.json()) as { interview_complete?: boolean }
      setTranscript("")
      setAudioFile(null)

      if (meta.interview_complete) {
        setPhase("done")
        setCurrentQuestion(null)
        const rr = await fetch(`/api/interview/${sessionId}/results`)
        if (!rr.ok) throw new Error(await readError(rr))
        setResults((await rr.json()) as ResultsPayload)
      } else {
        const hasNext = await refreshQuestion(sessionId)
        if (!hasNext) {
          setPhase("done")
          const rr = await fetch(`/api/interview/${sessionId}/results`)
          if (rr.ok) setResults((await rr.json()) as ResultsPayload)
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Submit failed.")
    } finally {
      setLoading(false)
    }
  }, [audioFile, currentQuestion, refreshQuestion, sessionId, transcript])

  const loadResultsOnly = useCallback(async () => {
    if (!sessionId) return
    setLoading(true)
    setError(null)
    try {
      const rr = await fetch(`/api/interview/${sessionId}/results`)
      if (!rr.ok) throw new Error(await readError(rr))
      setResults((await rr.json()) as ResultsPayload)
      setPhase("done")
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load results.")
    } finally {
      setLoading(false)
    }
  }, [sessionId])

  return (
    <div className="space-y-8">
      <ApiBackendBanner />
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Button variant="ghost" size="sm" asChild className="gap-1.5 text-muted-foreground">
          <Link href="/">
            <ArrowLeft className="h-4 w-4" aria-hidden="true" />
            Back to resume ranking
          </Link>
        </Button>
        {phase !== "setup" && (
          <Button type="button" variant="outline" size="sm" onClick={resetFlow}>
            New session
          </Button>
        )}
      </div>

      {phase === "setup" && (
        <section className="space-y-6 rounded-xl border border-border bg-card p-5 md:p-6">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Briefcase className="h-5 w-5" aria-hidden="true" />
            </div>
            <div>
              <h2 className="text-lg font-semibold tracking-tight">Role context</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                Starting the session generates <strong>five job-specific questions</strong> up front (one LLM batch when
                Groq is configured). On the <strong>Live camera</strong> tab, each answer is recorded for{" "}
                <strong>{LIVE_RECORD_SECONDS} seconds</strong> and sent automatically — no separate submit. Other tabs
                still use <strong>Submit answer</strong>.
              </p>
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="int-jd">Job description</Label>
            <Textarea
              id="int-jd"
              value={jobDescription}
              onChange={(e) => setJobDescription(e.target.value)}
              className="min-h-48 resize-y font-mono text-xs leading-relaxed"
              placeholder="Paste the job description…"
            />
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="int-skills">Skills (comma-separated)</Label>
              <Input
                id="int-skills"
                value={skillsRaw}
                onChange={(e) => setSkillsRaw(e.target.value)}
                placeholder="Python, PostgreSQL, …"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-2">
                <Label htmlFor="int-rs">Resume score (optional)</Label>
                <Input
                  id="int-rs"
                  inputMode="numeric"
                  value={resumeScore}
                  onChange={(e) => setResumeScore(e.target.value)}
                  placeholder="0–100"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="int-ts">Test score (optional)</Label>
                <Input
                  id="int-ts"
                  inputMode="numeric"
                  value={testScore}
                  onChange={(e) => setTestScore(e.target.value)}
                  placeholder="0–100"
                />
              </div>
            </div>
          </div>

          <Button size="lg" onClick={startInterview} disabled={loading} className="gap-2">
            {loading ? (
              <>
                <Spinner className="h-4 w-4" />
                Preparing questions…
              </>
            ) : (
              <>
                <Video className="h-4 w-4" aria-hidden="true" />
                Start interview session
              </>
            )}
          </Button>
        </section>
      )}

      {phase === "live" && sessionId && (
        <section className="space-y-6">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex flex-wrap items-center gap-2">
              <Badge variant="outline" className="font-mono text-[11px]">
                Session {sessionId.slice(0, 8)}…
              </Badge>
              {currentQuestion && (
                <Badge variant="secondary" className="text-[11px] tabular-nums">
                  Question {currentQuestion.order_index} of {totalQuestions}
                </Badge>
              )}
            </div>
            <span className="text-xs text-muted-foreground">Answers are not persisted in the browser.</span>
          </div>

          {currentQuestion ? (
            <div className="rounded-xl border border-border bg-card p-5 md:p-6">
              <div className="mb-4 flex items-center gap-2 text-primary">
                <ClipboardList className="h-4 w-4" aria-hidden="true" />
                <span className="text-xs font-medium uppercase tracking-wider">Question</span>
                <Badge variant="secondary" className="text-[10px]">
                  {currentQuestion.difficulty}
                </Badge>
                {currentQuestion.skill_target && (
                  <Badge variant="outline" className="text-[10px]">
                    {currentQuestion.skill_target}
                  </Badge>
                )}
              </div>
              <p className="text-sm leading-relaxed text-foreground">{currentQuestion.question_text}</p>

              <div className="mt-6 space-y-4">
                <Tabs value={answerTab} onValueChange={(v) => setAnswerTab(v as "text" | "audio" | "live")}>
                  <TabsList className="flex h-auto min-h-10 flex-wrap gap-1">
                    <TabsTrigger value="text" className="gap-1.5">
                      <MessageSquareText className="h-3.5 w-3.5" aria-hidden="true" />
                      Type answer
                    </TabsTrigger>
                    <TabsTrigger value="live" className="gap-1.5">
                      <Video className="h-3.5 w-3.5" aria-hidden="true" />
                      Live camera
                    </TabsTrigger>
                    <TabsTrigger value="audio" className="gap-1.5">
                      <UploadCloud className="h-3.5 w-3.5" aria-hidden="true" />
                      Upload file
                    </TabsTrigger>
                  </TabsList>
                  <TabsContent value="text" className="mt-3 space-y-2">
                    <Textarea
                      value={transcript}
                      onChange={(e) => setTranscript(e.target.value)}
                      className="min-h-36 text-sm"
                      placeholder="Write what you would say in a live interview…"
                    />
                    <p className="text-xs text-muted-foreground">
                      Sent to the server as a transcript (same path as speech-to-text output).
                    </p>
                  </TabsContent>
                  <TabsContent value="live" className="mt-3 space-y-2">
                    <p className="text-xs text-muted-foreground">
                      Start camera once. Each question: <strong>{LIVE_RECORD_SECONDS}s</strong> hands-free recording,
                      then auto-submit and next question.
                    </p>
                    <InterviewLiveCapture
                      sessionKey={sessionId}
                      answerSegmentKey={currentQuestion.id}
                      disabled={loading}
                      persistCameraAcrossQuestions
                      autoRecordSeconds={LIVE_RECORD_SECONDS}
                      onRecordingReady={(file) => {
                        setError(null)
                        void submitAnswerWithFile(file)
                      }}
                      onError={(m) => setError(m)}
                    />
                  </TabsContent>
                  <TabsContent value="audio" className="mt-3 space-y-2">
                    <Input
                      type="file"
                      accept="audio/*,.webm,.wav,.mp3,.m4a,.ogg"
                      onChange={(e) => setAudioFile(e.target.files?.[0] ?? null)}
                    />
                    <p className="text-xs text-muted-foreground">
                      Upload a clip for transcription (mock or Groq Whisper when{" "}
                      <code className="rounded bg-muted px-1">INTERVIEW_USE_GROQ_TRANSCRIPTION</code> is on).
                    </p>
                  </TabsContent>
                </Tabs>

                {answerTab !== "live" && audioFile && (
                  <p className="text-xs text-muted-foreground">
                    Ready to submit:{" "}
                    <span className="font-medium text-foreground">{audioFile.name}</span>{" "}
                    <span className="tabular-nums">({(audioFile.size / 1024).toFixed(0)} KB)</span>
                  </p>
                )}

                {answerTab !== "live" ? (
                  <Button size="lg" onClick={submitAnswer} disabled={loading} className="gap-2">
                    {loading ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                        Submitting…
                      </>
                    ) : (
                      <>
                        <Sparkles className="h-4 w-4" aria-hidden="true" />
                        Submit answer
                      </>
                    )}
                  </Button>
                ) : (
                  <p className="text-xs text-muted-foreground">
                    {loading
                      ? "Submitting answer and loading the next question…"
                      : `Live tab: wait for the ${LIVE_RECORD_SECONDS}s clip to finish — submission runs automatically.`}
                  </p>
                )}
              </div>
            </div>
          ) : (
            <Alert>
              <Trophy className="h-4 w-4" aria-hidden="true" />
              <AlertTitle>Interview complete</AlertTitle>
              <AlertDescription className="flex flex-col gap-3 sm:flex-row sm:items-center">
                <span>No more questions in this session.</span>
                <Button size="sm" variant="secondary" onClick={loadResultsOnly} disabled={loading}>
                  View results
                </Button>
              </AlertDescription>
            </Alert>
          )}
        </section>
      )}

      {phase === "done" && results && (
        <section className="space-y-6 rounded-xl border border-border bg-card p-5 md:p-6">
          <div>
            <p className="text-xs font-medium uppercase tracking-wider text-primary">Results</p>
            <h2 className="mt-1 text-xl font-semibold tracking-tight">Interview &amp; aggregate scores</h2>
            <p className="mt-1 text-sm text-muted-foreground">Status: {results.status}</p>
          </div>

          {results.hire_decision && (
            <div
              className={cn(
                "rounded-xl border p-5 md:p-6",
                results.hire_decision === "APPROVED"
                  ? "border-emerald-500/35 bg-emerald-500/[0.08]"
                  : "border-destructive/35 bg-destructive/[0.08]",
              )}
            >
              <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                Hiring recommendation
              </p>
              <p className="mt-2 text-xl font-semibold tracking-tight md:text-2xl">
                {results.hire_decision === "APPROVED" ? "Approved for the role" : "Not approved for the role"}
              </p>
              {results.hire_rationale ? (
                <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{results.hire_rationale}</p>
              ) : null}
            </div>
          )}

          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <ScoreCard label="Interview avg" value={results.interview_average} suffix="/ 100" highlight />
            <ScoreCard label="Combined" value={results.aggregated.combined} suffix="/ 100" />
            <ScoreCard label="Resume (input)" value={results.aggregated.resume} suffix="/ 100" />
            <ScoreCard label="Test (input)" value={results.aggregated.test} suffix="/ 100" />
          </div>

          <div className="rounded-lg border border-border bg-muted/30 px-3 py-2 text-xs text-muted-foreground">
            Weights: resume {results.aggregated.weights.resume?.toFixed(2) ?? "—"}, test{" "}
            {results.aggregated.weights.test?.toFixed(2) ?? "—"}, interview{" "}
            {results.aggregated.weights.interview?.toFixed(2) ?? "—"}
          </div>

          <div className="space-y-4">
            <h3 className="text-sm font-semibold">Per-question evaluations</h3>
            <ul className="space-y-3">
              {results.evaluations.map((ev, i) => (
                <li
                  key={`${ev.question_id}-${i}`}
                  className="rounded-lg border border-border bg-background/80 p-4 text-sm"
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-mono text-[11px] text-muted-foreground">{ev.question_id.slice(0, 8)}…</span>
                    <Badge variant="outline" className="text-[10px]">
                      {ev.rubric_id}
                    </Badge>
                  </div>
                  <div className="mt-2 flex flex-wrap gap-2 text-xs">
                    {typeof ev.scores.weighted_total === "number" && (
                      <Badge>Total {String(ev.scores.weighted_total)}</Badge>
                    )}
                    {typeof ev.scores.content_quality === "number" && (
                      <Badge variant="secondary">Content {String(ev.scores.content_quality)}</Badge>
                    )}
                    {typeof ev.scores.reasoning === "number" && (
                      <Badge variant="secondary">Reasoning {String(ev.scores.reasoning)}</Badge>
                    )}
                    {typeof ev.scores.communication_clarity === "number" && (
                      <Badge variant="secondary">Clarity {String(ev.scores.communication_clarity)}</Badge>
                    )}
                    {typeof ev.scores.text_sentiment === "string" && (
                      <Badge variant="outline">Sentiment: {ev.scores.text_sentiment}</Badge>
                    )}
                  </div>
                  <p className="mt-2 text-xs leading-relaxed text-muted-foreground">{ev.explanation}</p>
                  <p className="mt-1 text-[10px] text-muted-foreground">Model: {ev.model_id}</p>
                </li>
              ))}
            </ul>
          </div>
        </section>
      )}

      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" aria-hidden="true" />
          <AlertTitle>Something went wrong</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}
    </div>
  )
}

function ScoreCard({
  label,
  value,
  suffix,
  highlight,
}: {
  label: string
  value: number | null
  suffix?: string
  highlight?: boolean
}) {
  return (
    <div
      className={cn(
        "rounded-xl border p-4",
        highlight ? "border-primary/25 bg-primary/[0.06]" : "border-border bg-muted/20",
      )}
    >
      <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">{label}</p>
      <p className="mt-2 text-2xl font-semibold tabular-nums">
        {value == null ? "—" : value}
        {suffix && value != null && <span className="text-xs font-normal text-muted-foreground">{suffix}</span>}
      </p>
    </div>
  )
}
