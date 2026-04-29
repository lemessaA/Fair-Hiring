"use client"

import { useCallback, useRef, useState } from "react"
import Link from "next/link"
import { AlertCircle, Briefcase, FileText, Sparkles, Video } from "lucide-react"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Spinner } from "@/components/ui/spinner"
import { ApiBackendBanner } from "@/components/api-backend-banner"
import { CandidateResults } from "@/components/candidate-results"
import { FileUpload } from "@/components/file-upload"
import { JdInput } from "@/components/jd-input"

export type Candidate = {
  id: string
  filename: string
  score?: number
  matched_skills?: string[]
  missing_skills?: string[]
  strengths?: string
  gaps?: string
  summary?: string
  skills?: string[]
  years_experience?: number
  education_level?: string
  masked_resume?: string
  masking_report?: {
    emails: number
    phones: number
    addresses: number
    gendered_terms: number
  }
  error?: string
}

type RankResponse = {
  job_description: string
  candidate_count: number
  candidates: Candidate[]
}

const SAMPLE_JOB = `Senior Backend Engineer

We are hiring a senior backend engineer to design and build scalable APIs.

Requirements:
- 5+ years building production backend systems
- Strong Python skills, ideally with FastAPI or Django
- Experience with PostgreSQL and query optimization
- Familiarity with cloud platforms (AWS or GCP)
- Comfortable with CI/CD, observability and on-call rotations

Nice to have:
- Experience with LLM tooling (LangChain, LangGraph)
- Kubernetes or container orchestration
- Open source contributions`

export function RankingTool() {
  const [jobDescription, setJobDescription] = useState<string>(SAMPLE_JOB)
  const [files, setFiles] = useState<File[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<RankResponse | null>(null)
  const [fieldError, setFieldError] = useState<{ jd?: string; files?: string }>({})
  const resultsRef = useRef<HTMLDivElement | null>(null)

  const handleSubmit = useCallback(async () => {
    setError(null)
    const errs: { jd?: string; files?: string } = {}
    if (!jobDescription.trim()) errs.jd = "Job description is required."
    if (files.length === 0) errs.files = "Upload at least one PDF resume."
    setFieldError(errs)
    if (Object.keys(errs).length > 0) return

    setLoading(true)
    setResult(null)
    try {
      const formData = new FormData()
      formData.append("job_description", jobDescription)
      for (const f of files) formData.append("files", f)

      const res = await fetch("/api/rank", { method: "POST", body: formData })

      if (!res.ok) {
        let detail = `Request failed (${res.status})`
        try {
          const data = await res.json()
          if (data?.detail) detail = data.detail
        } catch {
          // ignore
        }
        throw new Error(detail)
      }

      const data = (await res.json()) as RankResponse
      setResult(data)
      requestAnimationFrame(() => {
        resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" })
      })
    } catch (e) {
      const message = e instanceof Error ? e.message : "Something went wrong."
      setError(message)
    } finally {
      setLoading(false)
    }
  }, [files, jobDescription])

  const jdWordCount = jobDescription.trim() ? jobDescription.trim().split(/\s+/).length : 0

  return (
    <div className="space-y-6">
      <ApiBackendBanner />
      <div className="grid gap-4 md:grid-cols-2 md:gap-5">
        {/* Step 1 — Job description */}
        <StepCard
          step="01"
          icon={<Briefcase className="h-4 w-4" aria-hidden="true" />}
          title="Job description"
          description="Paste the role requirements or upload a PDF. Skills and experience here drive the ranking."
          meta={`${jdWordCount} word${jdWordCount === 1 ? "" : "s"}`}
          invalid={!!fieldError.jd}
        >
          <JdInput
            value={jobDescription}
            onChange={setJobDescription}
            invalid={!!fieldError.jd}
            errorMessage={fieldError.jd}
          />
        </StepCard>

        {/* Step 2 — Resumes */}
        <StepCard
          step="02"
          icon={<FileText className="h-4 w-4" aria-hidden="true" />}
          title="Resumes"
          description="Upload one or more PDF resumes. Processed in-memory and never saved."
          meta={files.length ? `${files.length} ready` : "PDF only"}
          invalid={!!fieldError.files}
        >
          <FileUpload files={files} onChange={setFiles} error={fieldError.files} />
        </StepCard>
      </div>

      {/* Sticky CTA bar */}
      <div className="sticky bottom-4 z-20 mt-6 rounded-xl border border-border bg-card/90 p-3 shadow-lg backdrop-blur supports-[backdrop-filter]:bg-card/70">
        <div className="flex flex-col items-stretch gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
              <Sparkles className="h-4 w-4" aria-hidden="true" />
            </div>
            <div className="leading-tight">
              <p className="text-sm font-medium">
                {files.length === 0
                  ? "Step 03 — Rank candidates"
                  : `Ready to rank ${files.length} resume${files.length === 1 ? "" : "s"}`}
              </p>
              <p className="text-xs text-muted-foreground">
                {files.length === 0
                  ? "Add a JD and at least one resume."
                  : "PII will be masked locally before the model is called."}
              </p>
            </div>
          </div>
          <Button
            onClick={handleSubmit}
            disabled={loading}
            size="lg"
            className="shadow-sm sm:min-w-44"
            aria-busy={loading}
          >
            {loading ? (
              <>
                <Spinner className="mr-2" />
                Ranking...
              </>
            ) : (
              <>
                Rank candidates
                <Sparkles className="ml-2 h-4 w-4" aria-hidden="true" />
              </>
            )}
          </Button>
        </div>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" aria-hidden="true" />
          <AlertTitle>Could not rank resumes</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div ref={resultsRef}>{result && <CandidateResults result={result} />}</div>

      {result && (
        <div className="mt-10 flex flex-col items-center gap-3 rounded-xl border border-primary/25 bg-primary/[0.06] p-6 text-center md:p-8">
          <p className="text-sm font-semibold tracking-tight text-foreground">Next: video interview</p>
          <p className="max-w-lg text-xs leading-relaxed text-muted-foreground md:text-sm">
            Continue to a guided session with <strong>five AI-generated questions</strong> tailored to this role. On the
            live tab, each answer is recorded for <strong>30 seconds</strong> and sent automatically. At the end you get
            an <strong>approve / reject</strong> recommendation from combined resume and interview scores.
          </p>
          <Button asChild size="lg" className="gap-2 shadow-sm">
            <Link
              href="/interview"
              onClick={() => {
                const ranked = [...result.candidates]
                  .filter((c) => !c.error)
                  .sort((a, b) => (b.score ?? 0) - (a.score ?? 0))
                const top = ranked[0]
                const skillSet = Array.from(
                  new Set([...(top?.matched_skills ?? []), ...(top?.skills ?? [])]),
                )
                sessionStorage.setItem(
                  "fh_interview_prefill",
                  JSON.stringify({
                    jobDescription: result.job_description,
                    skills: skillSet.length > 0 ? skillSet : undefined,
                    resumeScore: typeof top?.score === "number" ? top.score : undefined,
                  }),
                )
              }}
            >
              <Video className="h-4 w-4" aria-hidden="true" />
              Continue to video interview
            </Link>
          </Button>
        </div>
      )}
    </div>
  )
}

function StepCard({
  step,
  icon,
  title,
  description,
  meta,
  invalid,
  children,
}: {
  step: string
  icon: React.ReactNode
  title: string
  description: string
  meta?: string
  invalid?: boolean
  children: React.ReactNode
}) {
  return (
    <div
      className={[
        "rounded-xl border bg-card p-5 transition-colors",
        invalid ? "border-destructive/40" : "border-border",
      ].join(" ")}
      data-invalid={invalid ? "true" : undefined}
    >
      <div className="mb-4 flex items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <div className="relative flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
            {icon}
            <span
              aria-hidden="true"
              className="absolute -right-1.5 -top-1.5 flex h-5 min-w-5 items-center justify-center rounded-full border border-border bg-background px-1 font-mono text-[10px] font-semibold tabular-nums text-muted-foreground"
            >
              {step}
            </span>
          </div>
          <div className="min-w-0">
            <h3 className="text-sm font-semibold tracking-tight">{title}</h3>
            <p className="mt-0.5 text-xs leading-relaxed text-muted-foreground">{description}</p>
          </div>
        </div>
        {meta && (
          <span className="shrink-0 rounded-full border border-border bg-muted/50 px-2 py-0.5 text-[10px] font-medium text-muted-foreground">
            {meta}
          </span>
        )}
      </div>
      {children}
    </div>
  )
}
