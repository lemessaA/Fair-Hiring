"use client"

import { useMemo, useState } from "react"
import {
  ChevronDown,
  ChevronUp,
  Crown,
  FileWarning,
  Minus,
  Plus,
  ShieldCheck,
  Sparkles,
  Trophy,
} from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Empty, EmptyHeader, EmptyTitle, EmptyDescription } from "@/components/ui/empty"
import type { Candidate } from "@/components/ranking-tool"

type Props = {
  result: {
    job_description: string
    candidate_count: number
    candidates: Candidate[]
  }
}

export function CandidateResults({ result }: Props) {
  const ranked = result.candidates.filter((c) => !c.error)
  const errored = result.candidates.filter((c) => !!c.error)

  const stats = useMemo(() => {
    const scores = ranked.map((c) => c.score ?? 0)
    const avg = scores.length ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length) : 0
    const top = scores.length ? Math.max(...scores) : 0
    const totalRedactions = ranked.reduce((acc, c) => {
      const r = c.masking_report
      if (!r) return acc
      return acc + r.emails + r.phones + r.addresses + r.gendered_terms
    }, 0)
    return { avg, top, totalRedactions }
  }, [ranked])

  if (result.candidates.length === 0) {
    return (
      <Empty>
        <EmptyHeader>
          <EmptyTitle>No candidates ranked</EmptyTitle>
          <EmptyDescription>Upload at least one resume to get started.</EmptyDescription>
        </EmptyHeader>
      </Empty>
    )
  }

  const [first, ...rest] = ranked

  return (
    <section className="mt-12 space-y-8" aria-label="Ranking results">
      {/* Header + stats */}
      <div className="space-y-5">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-xs font-medium uppercase tracking-wider text-primary">Results</p>
            <h2 className="mt-1 text-2xl font-semibold tracking-tight md:text-3xl">Ranked candidates</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              {ranked.length} ranked
              {errored.length > 0 ? `, ${errored.length} skipped` : ""} &middot; sorted by skill match
            </p>
          </div>
          <Badge variant="outline" className="gap-1.5 border-primary/20 bg-primary/5 text-primary">
            <ShieldCheck className="h-3.5 w-3.5" aria-hidden="true" />
            PII masked locally
          </Badge>
        </div>

        <div className="grid gap-3 sm:grid-cols-3">
          <StatTile label="Top score" value={`${stats.top}`} suffix="/ 100" tone="primary" />
          <StatTile label="Average score" value={`${stats.avg}`} suffix="/ 100" />
          <StatTile label="PII redactions" value={`${stats.totalRedactions}`} suffix="across all resumes" />
        </div>
      </div>

      {/* Top candidate spotlight */}
      {first && <TopCandidate candidate={first} />}

      {/* Remaining candidates */}
      {rest.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-sm font-semibold tracking-tight text-muted-foreground">Other candidates</h3>
          {rest.map((c, idx) => (
            <CandidateRow key={c.id} candidate={c} rank={idx + 2} />
          ))}
        </div>
      )}

      {/* Errored */}
      {errored.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-sm font-semibold tracking-tight text-muted-foreground">Skipped</h3>
          {errored.map((c) => (
            <div
              key={c.id}
              className="rounded-xl border border-destructive/30 bg-destructive/5 p-4"
            >
              <div className="flex items-start gap-2.5">
                <FileWarning className="mt-0.5 h-4 w-4 shrink-0 text-destructive" aria-hidden="true" />
                <div className="min-w-0">
                  <p className="text-sm font-medium">
                    {c.id} &middot; <span className="text-muted-foreground">{c.filename}</span>
                  </p>
                  <p className="mt-0.5 text-sm text-destructive">{c.error}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

function StatTile({
  label,
  value,
  suffix,
  tone = "default",
}: {
  label: string
  value: string
  suffix?: string
  tone?: "default" | "primary"
}) {
  return (
    <div
      className={[
        "rounded-xl border p-4",
        tone === "primary" ? "border-primary/20 bg-primary/[0.04]" : "border-border bg-card",
      ].join(" ")}
    >
      <p className="text-[11px] font-medium uppercase tracking-wider text-muted-foreground">{label}</p>
      <div className="mt-2 flex items-baseline gap-1.5">
        <span
          className={[
            "text-2xl font-semibold tabular-nums tracking-tight",
            tone === "primary" ? "text-primary" : "text-foreground",
          ].join(" ")}
        >
          {value}
        </span>
        {suffix && <span className="text-xs text-muted-foreground">{suffix}</span>}
      </div>
    </div>
  )
}

function scoreTone(score: number): { label: string; ring: string; text: string; bg: string } {
  if (score >= 80) return { label: "Strong match", ring: "ring-primary/30", text: "text-primary", bg: "bg-primary/10" }
  if (score >= 60) return { label: "Solid match", ring: "ring-chart-2/30", text: "text-chart-2", bg: "bg-chart-2/10" }
  if (score >= 40) return { label: "Partial match", ring: "ring-chart-4/30", text: "text-chart-4", bg: "bg-chart-4/10" }
  return { label: "Weak match", ring: "ring-border", text: "text-muted-foreground", bg: "bg-muted" }
}

function ScoreRing({ score }: { score: number }) {
  const radius = 36
  const circumference = 2 * Math.PI * radius
  const dash = (Math.max(0, Math.min(100, score)) / 100) * circumference
  const tone = scoreTone(score)
  return (
    <div className="relative flex h-24 w-24 shrink-0 items-center justify-center">
      <svg className="h-full w-full -rotate-90" viewBox="0 0 96 96" aria-hidden="true">
        <circle cx="48" cy="48" r={radius} className="fill-none stroke-muted" strokeWidth="6" />
        <circle
          cx="48"
          cy="48"
          r={radius}
          className={`fill-none ${tone.text}`}
          stroke="currentColor"
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={`${dash} ${circumference - dash}`}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-2xl font-semibold leading-none tabular-nums">{score}</span>
        <span className="text-[10px] uppercase tracking-wider text-muted-foreground">/ 100</span>
      </div>
    </div>
  )
}

function TopCandidate({ candidate }: { candidate: Candidate }) {
  const score = candidate.score ?? 0
  const tone = scoreTone(score)
  return (
    <div className="spotlight-ring relative overflow-hidden rounded-2xl border border-border bg-card shadow-[0_30px_80px_-30px_color-mix(in_oklab,var(--primary)_30%,transparent)]">
      {/* gradient accent header */}
      <div className="relative bg-gradient-to-br from-primary/15 via-primary/5 to-transparent px-5 pt-5 md:px-7 md:pt-7">
        <div className="absolute right-5 top-5 hidden md:block">
          <Badge className="gap-1 border-primary/30 bg-primary/10 text-primary" variant="outline">
            <Crown className="h-3 w-3" aria-hidden="true" />
            Top match
          </Badge>
        </div>

        <div className="flex flex-col items-start gap-4 sm:flex-row sm:items-center sm:gap-6">
          <ScoreRing score={score} />
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="rounded-md bg-primary/10 px-2 py-0.5 font-mono text-[11px] font-semibold text-primary">
                #1
              </span>
              <h3 className="truncate text-lg font-semibold tracking-tight">{candidate.id}</h3>
              <Badge variant="outline" className={`${tone.bg} ${tone.text} border-transparent`}>
                {tone.label}
              </Badge>
            </div>
            <p className="mt-0.5 truncate text-xs text-muted-foreground" title={candidate.filename}>
              {candidate.filename}
            </p>
            {candidate.summary && (
              <p className="mt-3 text-sm leading-relaxed text-foreground/90">{candidate.summary}</p>
            )}
          </div>
        </div>

        <MetaRow candidate={candidate} className="mt-5" />
      </div>

      <div className="space-y-5 px-5 py-5 md:px-7 md:py-6">
        <div className="grid gap-4 md:grid-cols-2">
          <SkillList title="Matched skills" tone="positive" skills={candidate.matched_skills} icon={<Plus className="h-3 w-3" aria-hidden="true" />} />
          <SkillList title="Missing skills" tone="negative" skills={candidate.missing_skills} icon={<Minus className="h-3 w-3" aria-hidden="true" />} />
        </div>

        {(candidate.strengths || candidate.gaps) && (
          <div className="grid gap-4 md:grid-cols-2">
            {candidate.strengths && <Insight title="Strengths" body={candidate.strengths} tone="positive" />}
            {candidate.gaps && <Insight title="Gaps" body={candidate.gaps} tone="negative" />}
          </div>
        )}

        <Disclosure id={candidate.id} candidate={candidate} defaultOpen />
      </div>
    </div>
  )
}

function CandidateRow({ candidate, rank }: { candidate: Candidate; rank: number }) {
  const [expanded, setExpanded] = useState(false)
  const score = candidate.score ?? 0
  const tone = scoreTone(score)

  return (
    <div className="overflow-hidden rounded-xl border border-border bg-card transition-colors hover:border-primary/20">
      <button
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
        aria-controls={`row-${candidate.id}`}
        className="flex w-full items-center gap-4 px-4 py-3.5 text-left transition-colors hover:bg-muted/30"
      >
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-muted font-mono text-xs font-semibold tabular-nums text-muted-foreground">
          {rank === 2 ? <Trophy className="h-4 w-4" aria-hidden="true" /> : `#${rank}`}
        </div>

        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="truncate text-sm font-semibold">{candidate.id}</p>
            <Badge variant="outline" className={`${tone.bg} ${tone.text} h-5 border-transparent text-[10px]`}>
              {tone.label}
            </Badge>
          </div>
          <p className="truncate text-xs text-muted-foreground" title={candidate.filename}>
            {candidate.filename}
          </p>
        </div>

        <div className="flex shrink-0 items-center gap-3">
          {/* mini bar */}
          <div className="hidden sm:flex sm:flex-col sm:items-end">
            <div className="h-1.5 w-28 overflow-hidden rounded-full bg-muted">
              <div
                className={`h-full ${tone.text}`}
                style={{ width: `${score}%`, backgroundColor: "currentColor" }}
                aria-hidden="true"
              />
            </div>
            <span className="mt-1 text-[10px] uppercase tracking-wider text-muted-foreground">
              skill fit
            </span>
          </div>
          <div className="text-right leading-none">
            <p className="text-2xl font-semibold tabular-nums">{score}</p>
            <p className="text-[10px] text-muted-foreground">/ 100</p>
          </div>
          {expanded ? (
            <ChevronUp className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
          ) : (
            <ChevronDown className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
          )}
        </div>
      </button>

      {expanded && (
        <div id={`row-${candidate.id}`} className="space-y-5 border-t border-border bg-muted/20 px-4 py-5">
          {candidate.summary && (
            <p className="text-sm leading-relaxed text-foreground/90">{candidate.summary}</p>
          )}
          <MetaRow candidate={candidate} />
          <div className="grid gap-4 md:grid-cols-2">
            <SkillList title="Matched skills" tone="positive" skills={candidate.matched_skills} icon={<Plus className="h-3 w-3" aria-hidden="true" />} />
            <SkillList title="Missing skills" tone="negative" skills={candidate.missing_skills} icon={<Minus className="h-3 w-3" aria-hidden="true" />} />
          </div>
          {(candidate.strengths || candidate.gaps) && (
            <div className="grid gap-4 md:grid-cols-2">
              {candidate.strengths && <Insight title="Strengths" body={candidate.strengths} tone="positive" />}
              {candidate.gaps && <Insight title="Gaps" body={candidate.gaps} tone="negative" />}
            </div>
          )}
          <Disclosure id={candidate.id} candidate={candidate} />
        </div>
      )}
    </div>
  )
}

function MetaRow({ candidate, className = "" }: { candidate: Candidate; className?: string }) {
  const report = candidate.masking_report
  const items: { label: string; value: string }[] = []
  if (typeof candidate.years_experience === "number")
    items.push({ label: "Experience", value: `${candidate.years_experience} yrs` })
  if (candidate.education_level)
    items.push({ label: "Education", value: candidate.education_level })
  if (report) {
    const total = report.emails + report.phones + report.addresses + report.gendered_terms
    items.push({ label: "Redactions", value: `${total}` })
  }
  if (items.length === 0) return null
  return (
    <div className={`flex flex-wrap gap-2 ${className}`}>
      {items.map((item) => (
        <div
          key={item.label}
          className="inline-flex items-center gap-1.5 rounded-full border border-border bg-background/80 px-2.5 py-1 text-xs"
        >
          <span className="text-muted-foreground">{item.label}</span>
          <span className="font-medium tabular-nums">{item.value}</span>
        </div>
      ))}
    </div>
  )
}

function SkillList({
  title,
  skills,
  tone,
  icon,
}: {
  title: string
  skills?: string[]
  tone: "positive" | "negative"
  icon?: React.ReactNode
}) {
  const isPositive = tone === "positive"
  return (
    <div>
      <p className="mb-2 flex items-center gap-1.5 text-xs font-medium uppercase tracking-wider text-muted-foreground">
        <span
          className={`flex h-4 w-4 items-center justify-center rounded-full ${
            isPositive ? "bg-primary/15 text-primary" : "bg-destructive/15 text-destructive"
          }`}
        >
          {icon}
        </span>
        {title}
      </p>
      {!skills || skills.length === 0 ? (
        <p className="text-sm text-muted-foreground">None identified.</p>
      ) : (
        <div className="flex flex-wrap gap-1.5">
          {skills.map((s) => (
            <Badge
              key={s}
              variant="outline"
              className={
                isPositive
                  ? "border-primary/25 bg-primary/10 text-primary"
                  : "border-destructive/25 bg-destructive/10 text-destructive"
              }
            >
              {s}
            </Badge>
          ))}
        </div>
      )}
    </div>
  )
}

function Insight({
  title,
  body,
  tone,
}: {
  title: string
  body: string
  tone: "positive" | "negative"
}) {
  const isPositive = tone === "positive"
  return (
    <div
      className={`rounded-lg border p-3.5 ${
        isPositive ? "border-primary/20 bg-primary/[0.04]" : "border-destructive/20 bg-destructive/[0.04]"
      }`}
    >
      <p className="mb-1 text-[11px] font-medium uppercase tracking-wider text-muted-foreground">{title}</p>
      <p className="text-sm leading-relaxed text-foreground/90">{body}</p>
    </div>
  )
}

function Disclosure({
  id,
  candidate,
  defaultOpen = false,
}: {
  id: string
  candidate: Candidate
  defaultOpen?: boolean
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="rounded-lg border border-border bg-background/60">
      <button
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-controls={`details-${id}`}
        className="flex w-full items-center justify-between gap-2 px-3.5 py-2.5 text-left text-xs font-medium text-muted-foreground transition-colors hover:text-foreground"
      >
        <span className="flex items-center gap-2">
          <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
          Inspect anonymized data sent to model
        </span>
        {open ? (
          <ChevronUp className="h-3.5 w-3.5" aria-hidden="true" />
        ) : (
          <ChevronDown className="h-3.5 w-3.5" aria-hidden="true" />
        )}
      </button>
      {open && (
        <div id={`details-${id}`} className="space-y-3 border-t border-border px-3.5 py-3">
          {candidate.skills && candidate.skills.length > 0 && (
            <div>
              <p className="mb-2 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                All extracted skills
              </p>
              <div className="flex flex-wrap gap-1.5">
                {candidate.skills.map((s) => (
                  <Badge key={s} variant="secondary" className="font-normal">
                    {s}
                  </Badge>
                ))}
              </div>
            </div>
          )}
          {candidate.masking_report && (
            <div>
              <p className="mb-2 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
                Redaction breakdown
              </p>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                <RedactionTile label="Emails" value={candidate.masking_report.emails} />
                <RedactionTile label="Phones" value={candidate.masking_report.phones} />
                <RedactionTile label="Addresses" value={candidate.masking_report.addresses} />
                <RedactionTile label="Gendered terms" value={candidate.masking_report.gendered_terms} />
              </div>
            </div>
          )}
          <div>
            <p className="mb-2 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
              Anonymized resume
            </p>
            <pre className="max-h-80 overflow-auto rounded-md border border-border bg-card p-3 text-[11px] leading-relaxed font-mono whitespace-pre-wrap">
              {candidate.masked_resume || "(empty)"}
            </pre>
          </div>
        </div>
      )}
    </div>
  )
}

function RedactionTile({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md border border-border bg-card px-2.5 py-2">
      <p className="text-lg font-semibold tabular-nums leading-none">{value}</p>
      <p className="mt-1 text-[10px] uppercase tracking-wider text-muted-foreground">{label}</p>
    </div>
  )
}

