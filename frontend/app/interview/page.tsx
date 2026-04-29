import Link from "next/link"
import { ArrowLeft, Scale, Video } from "lucide-react"
import { InterviewTool } from "@/components/interview-tool"

export default function InterviewPage() {
  return (
    <main className="min-h-svh bg-background">
      <header className="sticky top-0 z-30 border-b border-border/60 bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3.5 md:px-6">
          <Link href="/" className="flex items-center gap-2.5">
            <div className="relative flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-sm">
              <Scale className="h-[18px] w-[18px]" aria-hidden="true" />
            </div>
            <div className="leading-tight">
              <p className="text-sm font-semibold tracking-tight">Fair Hiring Network</p>
              <p className="text-[11px] text-muted-foreground">Video interview screening</p>
            </div>
          </Link>
          <ButtonGhostHome />
        </div>
      </header>

      <div className="mx-auto max-w-3xl px-4 py-10 md:px-6">
        <div className="mb-8 space-y-2">
          <div className="inline-flex items-center gap-2 rounded-full border border-primary/20 bg-primary/10 px-3 py-1 text-xs font-medium text-primary">
            <Video className="h-3.5 w-3.5" aria-hidden="true" />
            Live camera + mic (browser recording)
          </div>
          <h1 className="text-balance text-2xl font-semibold tracking-tight md:text-3xl">
            AI-guided interview
          </h1>
          <p className="max-w-2xl text-sm leading-relaxed text-muted-foreground">
            After resume ranking, open a session with <strong>five AI-generated questions</strong>. Use typing or
            upload if you prefer, or the <strong>Live camera</strong> tab for <strong>30-second</strong> hands-free
            answers that submit automatically. Scoring uses transcribed speech only — then you see an{" "}
            <strong>approve / reject</strong> recommendation for the role.
          </p>
        </div>

        <InterviewTool />
      </div>
    </main>
  )
}

function ButtonGhostHome() {
  return (
    <Link
      href="/"
      className="inline-flex items-center gap-1.5 rounded-md border border-border bg-card px-3 py-1.5 text-sm text-foreground transition-colors hover:bg-muted"
    >
      <ArrowLeft className="h-3.5 w-3.5" aria-hidden="true" />
      Home
    </Link>
  )
}
