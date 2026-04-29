"use client"

import { useEffect, useState } from "react"
import { AlertCircle, ServerCrash } from "lucide-react"
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"

/**
 * One-shot check that Next `/api/*` rewrites can reach the FastAPI backend.
 * Most "nothing works" cases are: only `next dev` is running, backend not on :8000.
 */
export function ApiBackendBanner() {
  const [state, setState] = useState<"checking" | "ok" | "down">("checking")

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const res = await fetch("/api/health", { method: "GET", cache: "no-store" })
        if (!cancelled) setState(res.ok ? "ok" : "down")
      } catch {
        if (!cancelled) setState("down")
      }
    })()
    return () => {
      cancelled = true
    }
  }, [])

  if (state === "checking" || state === "ok") return null

  return (
    <Alert variant="destructive" className="border-amber-500/50 bg-amber-500/10 text-amber-950 dark:text-amber-50">
      <ServerCrash className="h-4 w-4 text-amber-700 dark:text-amber-400" aria-hidden="true" />
      <AlertTitle className="flex items-center gap-1.5 text-amber-900 dark:text-amber-100">
        <AlertCircle className="h-4 w-4 shrink-0" aria-hidden="true" />
        Backend API unreachable
      </AlertTitle>
      <AlertDescription className="mt-2 space-y-2 text-sm text-amber-900/90 dark:text-amber-50/90">
        <p>
          This UI calls <code className="rounded bg-black/10 px-1 dark:bg-white/10">/api/…</code> on the Next
          server, which proxies to FastAPI (default dev:{" "}
          <code className="rounded bg-black/10 px-1 dark:bg-white/10">127.0.0.1:8000</code>).
        </p>
        <p className="font-medium">Fix — local dev: run the API in another terminal</p>
        <pre className="overflow-x-auto rounded-md border border-amber-500/30 bg-black/5 p-3 text-xs dark:bg-black/30">
{`cd backend
uv sync   # once
uv run uvicorn main:app --host 127.0.0.1 --port 8000 --reload`}
        </pre>
        <p>
          Or from the <code className="rounded bg-black/10 px-1">frontend</code> folder:{" "}
          <code className="rounded bg-black/10 px-1">npm run dev:full</code> (starts Next + backend together).
        </p>
        <p className="text-xs">
          <strong>Production (Vercel):</strong> set <code className="rounded bg-black/10 px-1">BACKEND_URL</code>{" "}
          to your FastAPI base URL (e.g. <code className="rounded bg-black/10 px-1">https://…fastapicloud.dev</code>
          , no trailing slash) in Vercel → Project → Settings → Environment Variables, then redeploy.
        </p>
        <p className="text-xs">
          Local override: <code className="rounded bg-black/10 px-1">frontend/.env.local</code>, then restart{" "}
          <code className="rounded bg-black/10 px-1">next dev</code>.
        </p>
      </AlertDescription>
    </Alert>
  )
}
