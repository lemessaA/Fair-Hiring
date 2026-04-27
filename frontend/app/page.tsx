import Link from "next/link"
import { ArrowRight, EyeOff, Github, Scale, ScanText, Sparkles, Target } from "lucide-react"
import { Badge } from "@/components/ui/badge"
import { RankingTool } from "@/components/ranking-tool"

export default function HomePage() {
  return (
    <main className="min-h-svh bg-background">
      {/* Header */}
      <header className="sticky top-0 z-30 border-b border-border/60 bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3.5 md:px-6">
          <Link href="/" className="flex items-center gap-2.5">
            <div className="relative flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-sm">
              <Scale className="h-[18px] w-[18px]" aria-hidden="true" />
            </div>
            <div className="leading-tight">
              <p className="text-sm font-semibold tracking-tight">Fair Hiring Network</p>
              <p className="text-[11px] text-muted-foreground">Skills-first resume ranking</p>
            </div>
          </Link>
          <nav aria-label="Primary" className="hidden items-center gap-1 text-sm md:flex">
            <a
              href="#how-it-works"
              className="rounded-md px-3 py-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            >
              How it works
            </a>
            <a
              href="#tool"
              className="rounded-md px-3 py-1.5 text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            >
              Try it
            </a>
            <a
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              className="ml-1 inline-flex items-center gap-1.5 rounded-md border border-border bg-card px-3 py-1.5 text-foreground transition-colors hover:bg-muted"
            >
              <Github className="h-3.5 w-3.5" aria-hidden="true" />
              Source
            </a>
          </nav>
        </div>
      </header>

      {/* Hero */}
      <section className="relative overflow-hidden">
        <div className="hero-mesh absolute inset-0 -z-10" aria-hidden="true" />
        <div className="dot-grid absolute inset-0 -z-10 opacity-50" aria-hidden="true" />
        <div className="hero-fade absolute inset-x-0 bottom-0 -z-10 h-40" aria-hidden="true" />

        <div className="mx-auto max-w-6xl px-4 pb-20 pt-16 md:px-6 md:pb-28 md:pt-24">
          <div className="mx-auto max-w-3xl text-center">
            <Badge
              variant="outline"
              className="mb-6 gap-1.5 border-primary/25 bg-primary/10 text-primary backdrop-blur"
            >
              <span className="relative flex h-1.5 w-1.5">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-primary opacity-70"></span>
                <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-primary"></span>
              </span>
              LangGraph + Groq, with PII masked locally
            </Badge>

            <h1 className="text-balance font-sans text-4xl font-semibold tracking-tight md:text-6xl md:leading-[1.05]">
              Rank candidates by{" "}
              <span className="relative inline-block">
                <span className="relative z-10 bg-gradient-to-br from-primary via-chart-2 to-chart-3 bg-clip-text text-transparent">
                  skills
                </span>
                <span
                  aria-hidden="true"
                  className="absolute -inset-x-2 inset-y-0 -z-0 rounded-2xl bg-primary/20 blur-2xl"
                />
              </span>
              ,
              <br className="hidden md:inline" /> not by who they are.
            </h1>

            <p className="mx-auto mt-5 max-w-2xl text-pretty text-base leading-relaxed text-muted-foreground md:text-lg">
              Drop in PDF resumes and a job description. We strip out emails, phones, addresses and gendered
              terms <em>before</em> any LLM sees them &mdash; so scoring focuses on what actually matters.
            </p>

            <div className="mt-9 flex flex-wrap items-center justify-center gap-3">
              <a
                href="#tool"
                className="group relative inline-flex items-center gap-2 overflow-hidden rounded-lg bg-primary px-5 py-2.5 text-sm font-medium text-primary-foreground shadow-[0_0_0_1px_rgba(255,255,255,0.08)_inset,0_10px_30px_-12px_color-mix(in_oklab,var(--primary)_60%,transparent)] transition-all hover:brightness-110"
              >
                <span
                  aria-hidden="true"
                  className="absolute inset-0 -translate-x-full bg-gradient-to-r from-transparent via-white/25 to-transparent transition-transform duration-700 group-hover:translate-x-full"
                />
                Start ranking
                <ArrowRight
                  className="h-4 w-4 transition-transform group-hover:translate-x-0.5"
                  aria-hidden="true"
                />
              </a>
              <a
                href="#how-it-works"
                className="inline-flex items-center gap-2 rounded-lg border border-border bg-card/60 px-5 py-2.5 text-sm font-medium text-foreground backdrop-blur transition-colors hover:bg-card"
              >
                How it works
              </a>
            </div>

            <div className="mt-10 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-xs text-muted-foreground">
              <span className="flex items-center gap-1.5">
                <EyeOff className="h-3.5 w-3.5" aria-hidden="true" />
                Resumes never leave your session
              </span>
              <span className="hidden h-3 w-px bg-border md:inline-block" aria-hidden="true" />
              <span className="flex items-center gap-1.5">
                <ScanText className="h-3.5 w-3.5" aria-hidden="true" />
                PII redacted before model call
              </span>
              <span className="hidden h-3 w-px bg-border md:inline-block" aria-hidden="true" />
              <span className="flex items-center gap-1.5">
                <Sparkles className="h-3.5 w-3.5" aria-hidden="true" />
                Groq Llama 3.3 70B
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* How it works */}
      <section
        id="how-it-works"
        className="relative border-y border-border/60 bg-[radial-gradient(ellipse_at_top,_color-mix(in_oklab,var(--primary)_8%,transparent),transparent_60%)]"
      >
        <div className="mx-auto max-w-6xl px-4 py-14 md:px-6 md:py-20">
          <div className="mx-auto mb-10 max-w-2xl text-center md:mb-14">
            <p className="text-xs font-medium uppercase tracking-wider text-primary">How it works</p>
            <h2 className="mt-2 text-balance text-2xl font-semibold tracking-tight md:text-3xl">
              Three steps to bias-aware ranking
            </h2>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            <FeatureCard
              step="01"
              icon={<EyeOff className="h-5 w-5" aria-hidden="true" />}
              title="Mask PII locally"
              description="Server-side regex strips emails, phones, addresses and gendered terms before any data leaves your environment."
            />
            <FeatureCard
              step="02"
              icon={<ScanText className="h-5 w-5" aria-hidden="true" />}
              title="Extract & score with LangGraph"
              description="A two-node graph extracts skills, then scores fit against the JD using Groq with strict structured output."
            />
            <FeatureCard
              step="03"
              icon={<Target className="h-5 w-5" aria-hidden="true" />}
              title="Inspect every decision"
              description="See matched / missing skills, strengths, gaps, and the exact anonymized text the model received."
            />
          </div>
        </div>
      </section>

      {/* Tool */}
      <section id="tool" className="mx-auto max-w-6xl px-4 py-14 md:px-6 md:py-20">
        <div className="mb-8 flex flex-wrap items-end justify-between gap-3 md:mb-10">
          <div>
            <p className="text-xs font-medium uppercase tracking-wider text-primary">Try it</p>
            <h2 className="mt-2 text-balance text-2xl font-semibold tracking-tight md:text-3xl">
              Rank a batch of resumes
            </h2>
          </div>
          <p className="text-sm text-muted-foreground">In-memory only &middot; nothing is persisted</p>
        </div>

        <RankingTool />
      </section>

      {/* Footer */}
      <footer className="border-t border-border/60 bg-muted/20">
        <div className="mx-auto flex max-w-6xl flex-col items-start justify-between gap-3 px-4 py-8 text-xs text-muted-foreground md:flex-row md:items-center md:px-6">
          <div className="flex items-center gap-2">
            <div className="flex h-6 w-6 items-center justify-center rounded-md bg-primary text-primary-foreground">
              <Scale className="h-3.5 w-3.5" aria-hidden="true" />
            </div>
            <p>
              Built with Next.js, FastAPI, LangGraph and Groq. For demonstration only &mdash; pair with a human reviewer.
            </p>
          </div>
          <p>&copy; {new Date().getFullYear()} Fair Hiring Network</p>
        </div>
      </footer>
    </main>
  )
}

function FeatureCard({
  step,
  icon,
  title,
  description,
}: {
  step: string
  icon: React.ReactNode
  title: string
  description: string
}) {
  return (
    <div className="group glass-card relative overflow-hidden rounded-xl p-6 transition-all hover:-translate-y-0.5">
      <div
        aria-hidden="true"
        className="pointer-events-none absolute -right-16 -top-16 h-40 w-40 rounded-full bg-primary/15 blur-3xl opacity-0 transition-opacity duration-500 group-hover:opacity-100"
      />
      <span
        className="absolute right-4 top-4 font-mono text-xs font-medium tabular-nums text-muted-foreground/60"
        aria-hidden="true"
      >
        {step}
      </span>
      <div className="mb-4 inline-flex h-10 w-10 items-center justify-center rounded-lg border border-primary/25 bg-primary/10 text-primary">
        {icon}
      </div>
      <h3 className="text-base font-semibold tracking-tight">{title}</h3>
      <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{description}</p>
    </div>
  )
}
