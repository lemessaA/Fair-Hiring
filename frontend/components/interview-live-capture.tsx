"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { Mic, Square, Video } from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

function pickAudioMimeType(): string | undefined {
  const candidates = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/mp4"]
  if (typeof MediaRecorder === "undefined" || !MediaRecorder.isTypeSupported) return undefined
  for (const c of candidates) {
    if (MediaRecorder.isTypeSupported(c)) return c
  }
  return undefined
}

export type InterviewLiveCaptureProps = {
  /** Cleared on change / unmount — tear down camera when the interview session ends. */
  sessionKey: string
  /** New question — reset recorder; camera may stay on when `persistCameraAcrossQuestions` is true. */
  answerSegmentKey: string
  onRecordingReady: (file: File) => void
  onError: (message: string) => void
  disabled?: boolean
  /** When true, only the MediaRecorder is reset between questions (continuous live session). */
  persistCameraAcrossQuestions?: boolean
  /** If set, each answer window is exactly this many seconds, then the clip is produced automatically. */
  autoRecordSeconds?: number | null
}

/**
 * Live camera preview + microphone. Recording uses **audio only** for `/submit-audio`.
 * With `autoRecordSeconds`, recording starts automatically after each `answerSegmentKey` change (camera on)
 * and stops when the timer elapses — no manual stop for submission.
 */
export function InterviewLiveCapture({
  sessionKey,
  answerSegmentKey,
  onRecordingReady,
  onError,
  disabled,
  persistCameraAcrossQuestions = false,
  autoRecordSeconds = null,
}: InterviewLiveCaptureProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const recorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const autoStopTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const recordedMimeRef = useRef<string>("audio/webm")

  const [cameraOn, setCameraOn] = useState(false)
  const [recording, setRecording] = useState(false)
  const [seconds, setSeconds] = useState(0)

  const stopTimer = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current)
      timerRef.current = null
    }
  }, [])

  const clearAutoStop = useCallback(() => {
    if (autoStopTimerRef.current) {
      clearTimeout(autoStopTimerRef.current)
      autoStopTimerRef.current = null
    }
  }, [])

  const stopMediaRecorder = useCallback(async () => {
    clearAutoStop()
    const rec = recorderRef.current
    if (!rec || rec.state === "inactive") {
      setRecording(false)
      stopTimer()
      setSeconds(0)
      return
    }
    await new Promise<void>((resolve) => {
      rec.addEventListener("stop", () => resolve(), { once: true })
      rec.stop()
    })
    recorderRef.current = null
    setRecording(false)
    stopTimer()
    setSeconds(0)
  }, [clearAutoStop, stopTimer])

  const stopCamera = useCallback(async () => {
    clearAutoStop()
    await stopMediaRecorder()
    streamRef.current?.getTracks().forEach((t) => t.stop())
    streamRef.current = null
    if (videoRef.current) {
      videoRef.current.srcObject = null
    }
    setCameraOn(false)
  }, [clearAutoStop, stopMediaRecorder])

  const stopMediaRecorderRef = useRef(stopMediaRecorder)
  stopMediaRecorderRef.current = stopMediaRecorder
  const stopCameraRef = useRef(stopCamera)
  stopCameraRef.current = stopCamera

  useEffect(() => {
    return () => {
      void stopCameraRef.current()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- only when session identity changes
  }, [sessionKey])

  useEffect(() => {
    return () => {
      if (persistCameraAcrossQuestions) void stopMediaRecorderRef.current()
      else void stopCameraRef.current()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- segment change only
  }, [answerSegmentKey, persistCameraAcrossQuestions])

  const startCamera = useCallback(async () => {
    if (disabled) return
    try {
      await stopCamera()
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: "user",
          width: { ideal: 640 },
          height: { ideal: 480 },
        },
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      })
      streamRef.current = stream
      const v = videoRef.current
      if (v) {
        v.srcObject = stream
        await v.play().catch(() => {})
      }
      setCameraOn(true)
    } catch (e) {
      const msg = e instanceof Error ? e.message : "Could not access camera or microphone."
      onError(`${msg} Check browser permissions (HTTPS or localhost required for getUserMedia).`)
    }
  }, [disabled, onError, stopCamera])

  const stopRecording = useCallback(async () => {
    clearAutoStop()
    const rec = recorderRef.current
    if (!rec || rec.state === "inactive") return
    const blobType = rec.mimeType || recordedMimeRef.current
    await new Promise<void>((resolve) => {
      rec.addEventListener("stop", () => resolve(), { once: true })
      rec.stop()
    })
    recorderRef.current = null
    setRecording(false)
    stopTimer()
    setSeconds(0)
    const blob = new Blob(chunksRef.current, { type: blobType })
    chunksRef.current = []
    if (blob.size < 256) {
      onError("Recording too short — speak for at least one second.")
      return
    }
    const ext = blobType.includes("ogg") ? "ogg" : blobType.includes("mp4") ? "m4a" : "webm"
    const file = new File([blob], `live-answer-${Date.now()}.${ext}`, { type: blobType })
    onRecordingReady(file)
  }, [clearAutoStop, onError, onRecordingReady, stopTimer])

  const startRecording = useCallback(async () => {
    if (disabled) return
    const stream = streamRef.current
    if (!stream) {
      onError("Turn on camera & microphone first.")
      return
    }
    const audioTrack = stream.getAudioTracks()[0]
    if (!audioTrack) {
      onError("No audio track — check your microphone.")
      return
    }
    await stopMediaRecorder()
    chunksRef.current = []
    const audioOnly = new MediaStream([audioTrack])
    const mime = pickAudioMimeType()
    const rec = mime ? new MediaRecorder(audioOnly, { mimeType: mime }) : new MediaRecorder(audioOnly)
    recordedMimeRef.current = rec.mimeType || mime || "audio/webm"
    rec.ondataavailable = (ev) => {
      if (ev.data.size > 0) chunksRef.current.push(ev.data)
    }
    rec.onerror = () => onError("MediaRecorder error.")
    rec.start(250)
    recorderRef.current = rec
    setRecording(true)
    setSeconds(0)
    timerRef.current = setInterval(() => setSeconds((s) => s + 1), 1000)

    if (autoRecordSeconds && autoRecordSeconds > 0) {
      autoStopTimerRef.current = setTimeout(() => {
        void stopRecording()
      }, autoRecordSeconds * 1000)
    }
  }, [autoRecordSeconds, disabled, onError, stopMediaRecorder, stopRecording])

  const startRecordingRef = useRef(startRecording)
  startRecordingRef.current = startRecording
  const clearAutoStopRef = useRef(clearAutoStop)
  clearAutoStopRef.current = clearAutoStop

  useEffect(() => {
    if (!autoRecordSeconds || autoRecordSeconds <= 0 || disabled) return
    if (!cameraOn || !answerSegmentKey) return
    let cancelled = false
    ;(async () => {
      await stopMediaRecorderRef.current()
      await new Promise<void>((r) => setTimeout(r, 450))
      if (cancelled || disabled) return
      await startRecordingRef.current()
    })()
    return () => {
      cancelled = true
      clearAutoStopRef.current()
    }
  }, [answerSegmentKey, autoRecordSeconds, cameraOn, disabled])

  const fmt = (s: number) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`
  const remaining = autoRecordSeconds && recording ? Math.max(0, autoRecordSeconds - seconds) : null

  return (
    <div className="space-y-4">
      <div
        className={cn(
          "relative aspect-video max-h-[280px] w-full overflow-hidden rounded-lg border border-border bg-black/80",
          !cameraOn && "flex items-center justify-center",
        )}
      >
        <video
          ref={videoRef}
          className={cn("h-full w-full object-cover", !cameraOn && "hidden")}
          playsInline
          muted
          autoPlay
        />
        {!cameraOn && (
          <p className="px-4 text-center text-sm text-muted-foreground">
            Camera preview here. Audio is scored after transcription; video is not sent to the model.
          </p>
        )}
        {recording && (
          <div className="absolute left-3 top-3 flex flex-col gap-1 rounded-lg bg-destructive/90 px-3 py-1.5 text-xs font-medium text-destructive-foreground shadow">
            <div className="flex items-center gap-2">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-white opacity-75" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-white" />
              </span>
              REC {fmt(seconds)}
              {remaining != null && (
                <span className="tabular-nums opacity-90">· {remaining}s left</span>
              )}
            </div>
            {autoRecordSeconds ? (
              <span className="text-[10px] font-normal opacity-90">Auto-submit when timer ends</span>
            ) : null}
          </div>
        )}
      </div>

      <div className="flex flex-wrap gap-2">
        {!cameraOn ? (
          <Button type="button" variant="default" size="sm" onClick={() => void startCamera()} disabled={disabled}>
            <Video className="mr-2 h-4 w-4" aria-hidden="true" />
            Start camera &amp; microphone
          </Button>
        ) : (
          <>
            <Button type="button" variant="outline" size="sm" onClick={() => void stopCamera()} disabled={disabled}>
              Stop camera
            </Button>
            {!autoRecordSeconds ? (
              !recording ? (
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => void startRecording()}
                  disabled={disabled}
                >
                  <Mic className="mr-2 h-4 w-4" aria-hidden="true" />
                  Start answer recording
                </Button>
              ) : (
                <Button
                  type="button"
                  variant="destructive"
                  size="sm"
                  onClick={() => void stopRecording()}
                  disabled={disabled}
                >
                  <Square className="mr-2 h-3.5 w-3.5 fill-current" aria-hidden="true" />
                  Stop &amp; attach clip
                </Button>
              )
            ) : (
              <p className="self-center text-xs text-muted-foreground">
                Hands-free mode: <strong>{autoRecordSeconds}s</strong> per question, then your answer is sent
                automatically.
              </p>
            )}
          </>
        )}
      </div>

      {!autoRecordSeconds ? (
        <p className="text-xs leading-relaxed text-muted-foreground">
          After <strong>Stop &amp; attach clip</strong>, press <strong>Submit answer</strong> below.
        </p>
      ) : (
        <p className="text-xs leading-relaxed text-muted-foreground">
          Start the camera once. For each question we record <strong>{autoRecordSeconds} seconds</strong> of audio,
          upload it, and move to the next question without a separate submit step.
        </p>
      )}
    </div>
  )
}
