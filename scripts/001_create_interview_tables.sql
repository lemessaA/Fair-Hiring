-- Create interview tables for Fair Hiring Network
-- Targets Supabase (PostgreSQL)

CREATE TABLE IF NOT EXISTS interview_session (
    id VARCHAR(36) PRIMARY KEY,
    status VARCHAR(32) NOT NULL DEFAULT 'CREATED',
    job_description TEXT NOT NULL,
    skills_json TEXT NOT NULL DEFAULT '[]',
    resume_score DOUBLE PRECISION,
    test_score DOUBLE PRECISION,
    webrtc_meta_json TEXT NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    joined_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    hire_decision VARCHAR(16),
    hire_rationale TEXT
);

CREATE TABLE IF NOT EXISTS interview_question (
    id VARCHAR(36) PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL REFERENCES interview_session(id) ON DELETE CASCADE,
    order_index INTEGER NOT NULL DEFAULT 0,
    question_text TEXT NOT NULL,
    skill_target VARCHAR(512) NOT NULL DEFAULT '',
    difficulty VARCHAR(32) NOT NULL DEFAULT 'mid',
    generated_json JSONB
);
CREATE INDEX IF NOT EXISTS idx_interview_question_session_id ON interview_question(session_id);

CREATE TABLE IF NOT EXISTS transcript_segment (
    id VARCHAR(36) PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL REFERENCES interview_session(id) ON DELETE CASCADE,
    question_id VARCHAR(36) REFERENCES interview_question(id) ON DELETE SET NULL,
    t_start_ms INTEGER NOT NULL DEFAULT 0,
    t_end_ms INTEGER NOT NULL DEFAULT 0,
    text TEXT NOT NULL,
    source VARCHAR(32) NOT NULL DEFAULT 'upload'
);
CREATE INDEX IF NOT EXISTS idx_transcript_segment_session_id ON transcript_segment(session_id);

CREATE TABLE IF NOT EXISTS candidate_response (
    id VARCHAR(36) PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL REFERENCES interview_session(id) ON DELETE CASCADE,
    question_id VARCHAR(36) NOT NULL REFERENCES interview_question(id) ON DELETE CASCADE,
    transcript_text TEXT NOT NULL,
    audio_ref VARCHAR(1024)
);
CREATE INDEX IF NOT EXISTS idx_candidate_response_session_id ON candidate_response(session_id);
CREATE INDEX IF NOT EXISTS idx_candidate_response_question_id ON candidate_response(question_id);

CREATE TABLE IF NOT EXISTS evaluation_result (
    id VARCHAR(36) PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL REFERENCES interview_session(id) ON DELETE CASCADE,
    question_id VARCHAR(36) NOT NULL REFERENCES interview_question(id) ON DELETE CASCADE,
    rubric_id VARCHAR(64) NOT NULL DEFAULT 'software_engineer_v1',
    scores_json JSONB NOT NULL,
    explanation TEXT NOT NULL DEFAULT '',
    model_id VARCHAR(128) NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_evaluation_result_session_id ON evaluation_result(session_id);
CREATE INDEX IF NOT EXISTS idx_evaluation_result_question_id ON evaluation_result(question_id);

CREATE TABLE IF NOT EXISTS interview_audit_log (
    id VARCHAR(36) PRIMARY KEY,
    session_id VARCHAR(36) NOT NULL REFERENCES interview_session(id) ON DELETE CASCADE,
    event_type VARCHAR(64) NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_interview_audit_log_session_id ON interview_audit_log(session_id);
