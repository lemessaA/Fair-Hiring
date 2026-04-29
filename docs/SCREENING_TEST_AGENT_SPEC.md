# Screening Test Agent — Feature Specification

Design goals for extending **Fair Hiring Network** (or a sibling module) with role-specific screening assessments that complement existing resume ranking and PII masking.

## Alignment with the current codebase

| Already in place | Relevant spec areas |
|------------------|---------------------|
| JD ingestion (paste + PDF extract) | 1 (Test generation input), 10 (templates) |
| Groq + LangGraph structured outputs | 1, 3 (generation + rubric scoring) |
| PII masking before LLM | 5 (blind evaluation), 11 (anonymization) |
| Multi-candidate batch + sorted results | 7 (dashboard thinking), export TBD |
| Explainable skill lists / strengths / gaps | 3, 9 (partial overlap) |

Everything else in this document is **new surface area** (persistence, timers, question banks, auth, anti-cheat telemetry, analytics stores, ATS exports).

---

## 1. Test generation

- Auto-generate role-specific screening tests from job descriptions
- Support multiple test types (coding, case study, situational, MCQ)
- Difficulty level control (junior, mid, senior)
- Question variation to reduce memorization and bias
- Skill-based test mapping (each question tied to a specific skill)

## 2. Candidate interaction

- Chat-based or form-based test interface
- Clear instructions and constraints (time, format, rules)
- Time-limited assessments
- Auto-save responses
- Multi-step problem handling
- Accessibility support (simple language mode, optional hints)

## 3. Evaluation & scoring

- Rubric-based scoring system
- Multi-criteria evaluation (accuracy, reasoning, clarity, efficiency)
- Structured output scoring (numeric + qualitative feedback)
- Consistent scoring across candidates
- Partial credit support
- Explainable scoring (why candidate got score)

## 4. Anti-cheating mechanisms

- Randomized question sets
- Question pools with dynamic selection
- Time tracking and anomaly detection
- Require reasoning/explanations for answers
- Plagiarism/similarity detection (for text/code)

## 5. Fairness & bias reduction

- Blind evaluation (no personal identifiers)
- Standardized difficulty across candidates
- Bias-audited question sets
- Language simplification options
- Cultural neutrality in scenarios
- Score normalization across cohorts

## 6. Adaptive testing (optional advanced)

- Dynamic difficulty adjustment based on answers
- Personalized question paths
- Early termination for clear pass/fail cases

## 7. Integration with hiring pipeline

- Combine test scores with resume ranking
- Configurable weighting system
- Candidate ranking dashboard
- Export results (API / CSV / ATS integration)
- Feedback loop with hiring outcomes

## 8. Analytics & insights

- Candidate performance analytics
- Question effectiveness tracking
- Drop-off and completion rates
- Skill gap analysis
- Hiring success correlation (test vs job performance)

## 9. Feedback & reporting

- Automated candidate feedback reports
- Recruiter evaluation summaries
- Strengths and weaknesses breakdown
- Improvement suggestions for candidates

## 10. Admin & configuration

- Custom test templates
- Role-based test configuration
- Scoring weight adjustment
- Question bank management
- Audit logs and version control

## 11. Security & privacy

- Secure data handling
- Candidate data anonymization
- Access control for recruiters/admins
- Compliance-ready design (GDPR-like principles)

## 12. Continuous improvement

- Model retraining using hiring outcomes
- A/B testing of test formats
- Human-in-the-loop review system
- Feedback-driven test refinement

---

## Suggested phasing (implementation hint)

1. **MVP:** Sections **1 + 3** (generate short MCQ/situational from JD, submit answers, rubric + structured score + explanation) using existing FastAPI + LangGraph patterns; no persistence beyond session.
2. **Next:** **2** (timer, autosave to localStorage), **7** (merge test score with resume score in UI with configurable weights).
3. **Then:** **4, 5, 10** (pools, normalization, admin config, audit logs) — requires DB and auth.
4. **Later:** **6, 8, 9, 11, 12** (adaptive, analytics, full reporting, compliance hardening, outcome loops).
