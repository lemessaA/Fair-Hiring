"use client"

import { useCallback, useRef, useState, type DragEvent } from "react"
import { AlertCircle, FileText, Trash2, UploadCloud } from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

type FileUploadProps = {
  files: File[]
  onChange: (files: File[]) => void
  error?: string
}

const MAX_FILES = 20
const MAX_SIZE_MB = 8

export function FileUpload({ files, onChange, error }: FileUploadProps) {
  const inputRef = useRef<HTMLInputElement | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const [localError, setLocalError] = useState<string | null>(null)

  const accept = useCallback(
    (incoming: FileList | File[]) => {
      const list = Array.from(incoming)
      const pdfs = list.filter((f) => f.type === "application/pdf" || f.name.toLowerCase().endsWith(".pdf"))
      if (pdfs.length === 0) {
        setLocalError("Only PDF files are supported.")
        return
      }
      const tooBig = pdfs.find((f) => f.size > MAX_SIZE_MB * 1024 * 1024)
      if (tooBig) {
        setLocalError(`Each file must be under ${MAX_SIZE_MB} MB.`)
        return
      }
      const next = [...files]
      for (const f of pdfs) {
        if (!next.some((existing) => existing.name === f.name && existing.size === f.size)) {
          next.push(f)
        }
      }
      if (next.length > MAX_FILES) {
        setLocalError(`At most ${MAX_FILES} resumes per ranking.`)
        return
      }
      setLocalError(null)
      onChange(next)
    },
    [files, onChange],
  )

  const onDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setDragOver(false)
    if (e.dataTransfer.files?.length) accept(e.dataTransfer.files)
  }

  const onDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setDragOver(true)
  }

  const removeAt = (idx: number) => {
    const next = files.slice()
    next.splice(idx, 1)
    onChange(next)
  }

  const visibleError = localError || error

  return (
    <div className="space-y-3">
      <div
        onDrop={onDrop}
        onDragOver={onDragOver}
        onDragLeave={() => setDragOver(false)}
        className={cn(
          "group relative flex cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed border-border bg-background/60 px-4 py-10 text-center transition-all",
          "hover:border-primary/40 hover:bg-primary/[0.03]",
          dragOver && "scale-[1.01] border-primary bg-primary/[0.06]",
          visibleError && "border-destructive/60 bg-destructive/5",
        )}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault()
            inputRef.current?.click()
          }
        }}
        aria-label="Upload PDF resumes"
      >
        <div
          className={cn(
            "mb-3 flex h-11 w-11 items-center justify-center rounded-full border border-border bg-card text-muted-foreground transition-colors",
            "group-hover:border-primary/30 group-hover:bg-primary/10 group-hover:text-primary",
            dragOver && "border-primary/50 bg-primary/10 text-primary",
          )}
        >
          <UploadCloud className="h-5 w-5" aria-hidden="true" />
        </div>
        <p className="text-sm font-medium">
          Drop PDFs here or <span className="text-primary underline-offset-2 group-hover:underline">browse</span>
        </p>
        <p className="mt-1 text-xs text-muted-foreground">
          Up to {MAX_FILES} files &middot; {MAX_SIZE_MB} MB each
        </p>
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          multiple
          className="hidden"
          onChange={(e) => {
            if (e.target.files) accept(e.target.files)
            e.target.value = ""
          }}
        />
      </div>

      {visibleError && (
        <p className="flex items-center gap-1 text-xs text-destructive" role="alert">
          <AlertCircle className="h-3 w-3" aria-hidden="true" />
          {visibleError}
        </p>
      )}

      {files.length > 0 && (
        <ul
          className="divide-y divide-border overflow-hidden rounded-lg border border-border bg-card"
          aria-label="Selected resumes"
        >
          {files.map((f, idx) => (
            <li
              key={`${f.name}-${idx}`}
              className="flex items-center justify-between gap-2 px-3 py-2 transition-colors hover:bg-muted/40"
            >
              <div className="flex min-w-0 items-center gap-2.5">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary">
                  <FileText className="h-4 w-4" aria-hidden="true" />
                </div>
                <div className="min-w-0 leading-tight">
                  <p className="truncate text-sm font-medium" title={f.name}>
                    {f.name}
                  </p>
                  <p className="text-[11px] text-muted-foreground">{(f.size / 1024).toFixed(0)} KB</p>
                </div>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={(e) => {
                  e.stopPropagation()
                  removeAt(idx)
                }}
                aria-label={`Remove ${f.name}`}
                className="text-muted-foreground hover:text-destructive"
              >
                <Trash2 className="h-4 w-4" aria-hidden="true" />
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
