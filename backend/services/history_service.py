from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from models.schemas import AnalysisResponse, AnalysisSummary


DATABASE_PATH = Path(__file__).resolve().parent.parent / "data" / "analyses.db"


def _connect() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_history_store() -> None:
    with _connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS analyses (
                analysis_id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                resume_filename TEXT NOT NULL,
                job_description_filename TEXT NOT NULL,
                ats_score INTEGER NOT NULL,
                matched_keywords TEXT NOT NULL,
                missing_keywords TEXT NOT NULL,
                retrieved_context TEXT NOT NULL,
                agent_trace TEXT NOT NULL,
                strengths TEXT NOT NULL,
                weaknesses TEXT NOT NULL,
                suggestions TEXT NOT NULL,
                interview_questions TEXT NOT NULL,
                learning_roadmap TEXT NOT NULL,
                recruiter_feedback TEXT NOT NULL
            )
            """
        )
        connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_analyses_user_created_at ON analyses(user_id, created_at DESC)"
        )
        connection.commit()


def save_analysis(analysis: AnalysisResponse, *, user_id: int) -> AnalysisResponse:
    initialize_history_store()

    analysis_id = analysis.analysis_id or datetime.now(timezone.utc).strftime("ana-%Y%m%d%H%M%S%f")
    created_at = analysis.created_at or datetime.now(timezone.utc).isoformat()

    payload = analysis.model_copy(update={"analysis_id": analysis_id, "created_at": created_at})

    with _connect() as connection:
        connection.execute(
            """
            INSERT OR REPLACE INTO analyses (
                analysis_id,
                user_id,
                created_at,
                resume_filename,
                job_description_filename,
                ats_score,
                matched_keywords,
                missing_keywords,
                retrieved_context,
                agent_trace,
                strengths,
                weaknesses,
                suggestions,
                interview_questions,
                learning_roadmap,
                recruiter_feedback
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.analysis_id,
                user_id,
                payload.created_at,
                payload.resume_filename,
                payload.job_description_filename,
                payload.ats_score,
                json.dumps(payload.matched_keywords),
                json.dumps(payload.missing_keywords),
                json.dumps(payload.retrieved_context),
                json.dumps(payload.agent_trace),
                json.dumps(payload.strengths.model_dump()),
                json.dumps(payload.weaknesses.model_dump()),
                json.dumps(payload.suggestions.model_dump()),
                json.dumps(payload.interview_questions.model_dump()),
                json.dumps(payload.learning_roadmap.model_dump()),
                payload.recruiter_feedback,
            ),
        )
        connection.commit()

    return payload


def list_recent_analyses(*, user_id: int, limit: int = 10) -> list[AnalysisSummary]:
    initialize_history_store()

    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT analysis_id, created_at, resume_filename, job_description_filename, ats_score, matched_keywords, missing_keywords
            FROM analyses
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()

    analyses: list[AnalysisSummary] = []
    for row in rows:
        analyses.append(
            AnalysisSummary(
                analysis_id=row["analysis_id"],
                created_at=row["created_at"],
                resume_filename=row["resume_filename"],
                job_description_filename=row["job_description_filename"],
                ats_score=int(row["ats_score"]),
                matched_count=len(json.loads(row["matched_keywords"])),
                missing_count=len(json.loads(row["missing_keywords"])),
            )
        )

    return analyses


def get_analysis(*, analysis_id: str, user_id: int) -> AnalysisResponse | None:
    initialize_history_store()

    with _connect() as connection:
        row = connection.execute(
            """
            SELECT *
            FROM analyses
            WHERE analysis_id = ? AND user_id = ?
            """,
            (analysis_id, user_id),
        ).fetchone()

    if row is None:
        return None

    return AnalysisResponse(
        analysis_id=row["analysis_id"],
        created_at=row["created_at"],
        resume_filename=row["resume_filename"],
        job_description_filename=row["job_description_filename"],
        ats_score=int(row["ats_score"]),
        matched_keywords=json.loads(row["matched_keywords"]),
        missing_keywords=json.loads(row["missing_keywords"]),
        retrieved_context=json.loads(row["retrieved_context"]),
        agent_trace=json.loads(row["agent_trace"]),
        strengths=payload_section(row["strengths"]),
        weaknesses=payload_section(row["weaknesses"]),
        suggestions=payload_section(row["suggestions"]),
        interview_questions=payload_section(row["interview_questions"]),
        learning_roadmap=payload_section(row["learning_roadmap"]),
        recruiter_feedback=row["recruiter_feedback"],
    )


def remove_user_history(user_id: int) -> None:
    initialize_history_store()
    with _connect() as connection:
        connection.execute("DELETE FROM analyses WHERE user_id = ?", (user_id,))
        connection.commit()


def payload_section(raw_json: str):
    from models.schemas import SectionFeedback

    data = json.loads(raw_json)
    return SectionFeedback(**data)
