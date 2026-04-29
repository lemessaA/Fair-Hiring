# Fair Hiring Network — Features & Tech Stack

Overview of existing capabilities on the **backend** (FastAPI) and **frontend** (Next.js), plus shared tooling.

> **Note:** The docstring on `POST /rank` in `backend/main.py` still mentions “Gemini”; the implementation uses **Groq** via LangChain.

---

## Backend (FastAPI)

### API features

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Returns `status`, configured model name (`GROQ_MODEL` or default), and whether `GROQ_API_KEY` is set. |
| `POST /extract-jd` | Accepts a **PDF** job description, extracts text with **PyPDF**, returns `filename`, `word_count`, `text`. Validates PDF MIME/extension; fails if no extractable text (e.g. scanned image-only PDF). |
| `POST /rank` | Accepts **job description** (form field) and **one or more resume PDFs**. Parses PDFs, applies **local PII masking**, runs the **LangGraph** workflow (analyze → score), returns candidates sorted by score (errors last) with scores, skills, narrative fields, masked resume text, and masking report. |

### Other behavior

- **CORS** middleware allows all origins (`*`), methods, and headers (suitable for demos; tighten for production if needed).
- **Secrets:** `python-dotenv` loads `backend/.env` when present. **`GROQ_API_KEY`** is required for `/rank`. Optional **`GROQ_MODEL`** (default: `llama-3.3-70b-versatile`).

### PII masking (`backend/pii.py`)

Regex-based masking before any LLM call:

- Email addresses → `[EMAIL]`
- Phone numbers (multiple formats) → `[PHONE]`
- ZIP / postal codes, street-style lines, city/state patterns → `[POSTAL]` / `[ADDRESS]` / `[LOCATION]`
- Gendered terms and pronouns neutralized (e.g. he/she → they; honorifics → Mx.; etc.)

Returns a **per-category count** report for transparency in the UI.

### AI pipeline (`backend/graph.py`)

- **LangGraph** `StateGraph`: **`analyze`** then **`score`**.
- **LangChain** `ChatGroq` with **`with_structured_output`**.
- **Pydantic** schemas: `CandidateAnalysis` (skills, years of experience, education, summary) and `CandidateScore` (0–100 score, matched/missing skills, strengths, gaps).

### Backend technologies

| Tool | Role |
|------|------|
| Python ≥3.12 | Runtime (`pyproject.toml`) |
| FastAPI (`fastapi[standard]`) | HTTP API, file uploads |
| Uvicorn | Local ASGI server (`uv run uvicorn …`) |
| PyPDF (`PdfReader`) | PDF text extraction |
| python-dotenv | Local `.env` loading |
| LangChain | LLM orchestration |
| langchain-groq | Groq chat models |
| LangGraph | Two-step analyze/score graph |
| Pydantic | Structured LLM outputs |
| **Deployment** | Vercel **Services** — `vercel.json` → FastAPI at `/_/backend` |

---

## Frontend (Next.js)

### UI features

| Area | Description |
|------|-------------|
| **Home / landing** (`app/page.tsx`) | Header with nav anchors, hero, “How it works” (three steps), **Try it** section, footer. Uses badges, icons, gradient/marketing copy. |
| **Ranking tool** (`components/ranking-tool.tsx`) | Job description + resume upload side-by-side; sticky **Rank candidates** CTA; `fetch` to **`/api/rank`**; loading state; error alert; smooth scroll to results. |
| **JD input** (`components/jd-input.tsx`) | **Tabs:** paste (textarea) vs **upload PDF**; drag-and-drop + file picker; calls **`/api/extract-jd`**; ~4 MB max for JD PDF; success meta and clear; field validation. |
| **Resume upload** (`components/file-upload.tsx`) | Multi-file PDF drag-and-drop + browse; up to **20** files, **8 MB** each; dedupe by name+size; list with per-file remove. |
| **Results** (`components/candidate-results.tsx`) | Aggregate stats (top score, average, total redactions); top candidate spotlight with score ring; expandable rows; **Skipped** section for errors; matched/missing skills, strengths/gaps; disclosure panel with extracted skills, redaction breakdown, **full masked resume** preview. |
| **Sample JD** | Pre-filled example job description for quick demos. |

### Frontend technologies

| Tool | Role |
|------|------|
| Next.js 16 | App Router, static/optimized builds |
| React 19 | UI |
| TypeScript | Types |
| Tailwind CSS v4 | Styling (`@tailwindcss/postcss`) |
| Radix UI | Accessible primitives (tabs, alert, dialog patterns, etc.) |
| lucide-react | Icons |
| next/font (Geist, Geist Mono) | Typography |
| Vercel Analytics | Production analytics (`@vercel/analytics`) |
| **API routing** | `next.config.mjs` **rewrites** `/api/*` → `BACKEND_URL` (Vercel) or `http://127.0.0.1:8000` (local) |

Additional dependencies in `frontend/package.json` (e.g. **react-hook-form**, **zod**, **next-themes**, **Sonner**, **Recharts**) support the UI kit and future forms/charts; the main flow above uses `FormData` and fetch for ranking.

---

## Monorepo & deployment

| Item | Description |
|------|-------------|
| **Root** | `pnpm`, `pnpm-workspace.yaml` (workspace package: `frontend`) |
| **Backend** | `uv`, `pyproject.toml`, `uv.lock` |
| **Vercel** | `vercel.json` with `experimentalServices`: Next.js at `/`, FastAPI at `/_/backend` |

---

## Environment variables (summary)

| Variable | Where | Purpose |
|----------|--------|---------|
| `GROQ_API_KEY` | Backend (Vercel + local `.env`) | Required for `/rank` |
| `GROQ_MODEL` | Optional | Overrides default Groq model id |
| `BACKEND_URL` | Injected on Vercel for Next.js | Target for `/api/*` rewrites (do not override unless using a custom API base) |

See root **`.env.example`** for copy-paste guidance.
