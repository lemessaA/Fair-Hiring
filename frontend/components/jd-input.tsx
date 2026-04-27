"use client"

import { useCallback, useRef, useState, type DragEvent } from "react"
import { AlertCircle, CheckCircle2, FileText, Loader2, Pencil, UploadCloud, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"
import { cn } from "@/lib/utils"

type JdInputProps = {
  value: string
  onChange: (value: string) => void
  invalid?: boolean
  errorMessage?: string
}

const MAX_SIZE_MB = 4

type ExtractedMeta = {
  filename: string
  wordCount: number
} | null

export function JdInput({ value, onChange, invalid, errorMessage }: JdInputProps) {
  const inputRef = useRef<HTMLInputElement | null>(null)
  const [tab, setTab] = useState<"paste" | "upload">("paste")
  const [dragOver, setDragOver] = useState(false)
  const [extracting, setExtracting] = useState(false)
  const [extractError, setExtractError] = useState<string | null>(null)
  const [extracted, setExtracted] = useState<ExtractedMeta>(null)

  const submitFile = useCallback(
    async (file: File) => {
      setExtractError(null)
      const isPdf = file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf")
      if (!isPdf) {
        setExtractError("Only PDF files are supported.")
        return
      }
      if (file.size > MAX_SIZE_MB * 1024 * 1024) {
        setExtractError(`File must be under ${MAX_SIZE_MB} MB.`)
        return
      }

      setExtracting(true)
      try {
        const fd = new FormData()
        fd.append("file", file)
        const res = await fetch("/api/extract-jd", { method: "POST", body: fd })
        if (!res.ok) {
          let detail = `Could not parse PDF (${res.status})`
          try {
            const data = await res.json()
            if (data?.detail) detail = data.detail
          } catch {
            // ignore
          }
          throw new Error(detail)
        }
        const data = (await res.json()) as { filename: string; word_count: number; text: string }
        onChange(data.text)
        setExtracted({ filename: data.filename, wordCount: data.word_count })
        // jump back to paste tab so the user can review/edit the extracted text
        setTab("paste")
      } catch (e) {
        setExtractError(e instanceof Error ? e.message : "Could not parse PDF.")
      } finally {
        setExtracting(false)
      }
    },
    [onChange],
  )

  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setDragOver(false)
    const f = e.dataTransfer.files?.[0]
    if (f) submitFile(f)
  }

  const onDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setDragOver(true)
  }

  const clearExtraction = () => {
    setExtracted(null)
    onChange("")
  }

  return (
    <div className="space-y-3">
      <Tabs value={tab} onValueChange={(v) => setTab(v as typeof tab)}>
        <TabsList className="bg-muted/40">
          <TabsTrigger value="paste" className="gap-1.5">
            <Pencil className="h-3.5 w-3.5" aria-hidden="true" />
            Paste
          </TabsTrigger>
          <TabsTrigger value="upload" className="gap-1.5">
            <UploadCloud className="h-3.5 w-3.5" aria-hidden="true" />
            Upload PDF
          </TabsTrigger>
        </TabsList>

        <TabsContent value="paste" className="mt-3 space-y-2">
          {extracted && (
            <div className="flex items-center justify-between gap-2 rounded-lg border border-primary/25 bg-primary/10 px-3 py-2 text-xs">
              <div className="flex min-w-0 items-center gap-2 text-primary">
                <CheckCircle2 className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                <span className="truncate font-medium" title={extracted.filename}>
                  Imported from {extracted.filename}
                </span>
                <span className="shrink-0 text-primary/70">
                  &middot; {extracted.wordCount} words
                </span>
              </div>
              <button
                type="button"
                onClick={clearExtraction}
                className="rounded-md p-1 text-primary/80 transition-colors hover:bg-primary/15 hover:text-primary"
                aria-label="Clear imported job description"
              >
                <X className="h-3.5 w-3.5" aria-hidden="true" />
              </button>
            </div>
          )}

          <Textarea
            id="jd"
            value={value}
            onChange={(e) => {
              onChange(e.target.value)
              if (extracted) setExtracted(null)
            }}
            placeholder="Paste the full job description here..."
            className={cn(
              "min-h-64 resize-y border-border/70 bg-background font-mono text-xs leading-relaxed focus-visible:border-primary/40 focus-visible:ring-primary/20",
              invalid && "border-destructive/60",
            )}
            aria-invalid={invalid ? true : undefined}
            aria-describedby="jd-help"
          />
          <p id="jd-help" className="text-xs text-muted-foreground">
            The model will only score candidates against what is written here.
          </p>
          {invalid && errorMessage && (
            <p className="flex items-center gap-1 text-xs text-destructive" role="alert">
              <AlertCircle className="h-3 w-3" aria-hidden="true" />
              {errorMessage}
            </p>
          )}
        </TabsContent>

        <TabsContent value="upload" className="mt-3 space-y-2">
          <div
            onDrop={onDrop}
            onDragOver={onDragOver}
            onDragLeave={() => setDragOver(false)}
            onClick={() => !extracting && inputRef.current?.click()}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault()
                if (!extracting) inputRef.current?.click()
              }
            }}
            className={cn(
              "group relative flex cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed border-border bg-background/60 px-4 py-12 text-center transition-all",
              "hover:border-primary/40 hover:bg-primary/[0.03]",
              dragOver && "scale-[1.01] border-primary bg-primary/[0.06]",
              extractError && "border-destructive/60 bg-destructive/5",
              extracting && "pointer-events-none opacity-80",
            )}
            aria-label="Upload job description PDF"
            aria-busy={extracting}
          >
            <div
              className={cn(
                "mb-3 flex h-11 w-11 items-center justify-center rounded-full border border-border bg-card text-muted-foreground transition-colors",
                "group-hover:border-primary/30 group-hover:bg-primary/10 group-hover:text-primary",
                dragOver && "border-primary/50 bg-primary/10 text-primary",
              )}
            >
              {extracting ? (
                <Loader2 className="h-5 w-5 animate-spin text-primary" aria-hidden="true" />
              ) : (
                <FileText className="h-5 w-5" aria-hidden="true" />
              )}
            </div>
            <p className="text-sm font-medium">
              {extracting ? (
                "Extracting text..."
              ) : (
                <>
                  Drop a JD PDF here or{" "}
                  <span className="text-primary underline-offset-2 group-hover:underline">browse</span>
                </>
              )}
            </p>
            <p className="mt-1 text-xs text-muted-foreground">
              Single PDF &middot; up to {MAX_SIZE_MB} MB &middot; text-based PDFs only
            </p>
            <input
              ref={inputRef}
              type="file"
              accept="application/pdf"
              className="hidden"
              onChange={(e) => {
                const f = e.target.files?.[0]
                if (f) submitFile(f)
                e.target.value = ""
              }}
            />
          </div>
          {extractError && (
            <p className="flex items-center gap-1 text-xs text-destructive" role="alert">
              <AlertCircle className="h-3 w-3" aria-hidden="true" />
              {extractError}
            </p>
          )}
          <p className="text-xs text-muted-foreground">
            We extract the text in-memory, then drop you back into the editor so you can review or
            tweak it before ranking.
          </p>
          {extracted && !extractError && (
            <div className="flex items-center gap-2 rounded-lg border border-primary/25 bg-primary/10 px-3 py-2 text-xs text-primary">
              <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
              <span className="truncate font-medium" title={extracted.filename}>
                {extracted.filename}
              </span>
              <span className="text-primary/70">&middot; {extracted.wordCount} words</span>
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation()
                  setTab("paste")
                }}
                className="ml-auto h-7 px-2 text-primary hover:bg-primary/15 hover:text-primary"
              >
                Review
              </Button>
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}
