from __future__ import annotations

import os
import re
from collections import Counter
from textwrap import dedent

from models.schemas import AnalysisResponse, SectionFeedback
from rag.chunking import split_text_into_chunks
from rag.vector_store import LocalVectorStore
from services.gemini_service import generate_gemini_analysis


STOPWORDS = {
    "and",
    "or",
    "the",
    "a",
    "an",
    "to",
    "of",
    "in",
    "for",
    "with",
    "on",
    "at",
    "by",
    "from",
    "as",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "it",
    "that",
    "this",
    "you",
    "your",
    "we",
    "our",
    "they",
    "their",
    "into",
    "using",
    "use",
    "role",
    "job",
    "candidate",
}

SECTION_HEADERS = {
    "skills": ["skills", "technical skills", "core skills", "tools"],
    "experience": ["experience", "work experience", "employment", "professional experience"],
    "projects": ["projects", "project experience", "selected projects"],
    "education": ["education", "academic background"],
    "summary": ["summary", "profile", "about"],
    "responsibilities": ["responsibilities", "duties", "what you will do"],
}


def _tokenize(text: str) -> list[str]:
    return [
        token.lower()
        for token in re.findall(r"[A-Za-z][A-Za-z0-9+.#-]*", text)
        if token.lower() not in STOPWORDS and len(token) > 1
    ]


def _top_keywords(text: str, limit: int = 20) -> list[str]:
    counts = Counter(_tokenize(text))
    return [keyword for keyword, _ in counts.most_common(limit)]


def _split_by_headings(text: str) -> dict[str, str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    sections: dict[str, list[str]] = {name: [] for name in SECTION_HEADERS}
    current_section = "summary"

    for line in lines:
        normalized = line.lower().rstrip(":")
        matched = next(
            (section_name for section_name, aliases in SECTION_HEADERS.items() if normalized in aliases),
            None,
        )
        if matched:
            current_section = matched
            continue

        sections.setdefault(current_section, []).append(line)

    return {name: " ".join(parts).strip() for name, parts in sections.items() if " ".join(parts).strip()}


def _section_feedback(title: str, items: list[str]) -> SectionFeedback:
    return SectionFeedback(title=title, items=items)


def _score_overlap(resume_keywords: set[str], job_keywords: list[str]) -> tuple[int, list[str], list[str]]:
    matched_keywords = [keyword for keyword in job_keywords if keyword in resume_keywords]
    missing_keywords = [keyword for keyword in job_keywords if keyword not in resume_keywords]
    score_base = len(job_keywords) or 1
    ats_score = round((len(matched_keywords) / score_base) * 100)
    return ats_score, matched_keywords, missing_keywords


def _build_recruiter_feedback(score: int, missing_keywords: list[str], matched_keywords: list[str]) -> str:
    if score >= 80:
        return (
            "Strong match signal. The resume already covers many of the JD keywords, so the main work is "
            "to sharpen impact bullets and add more concrete proof for the remaining gaps."
        )

    if score >= 60:
        return (
            "Moderate match signal. The resume shows a solid base, but several core JD keywords are still missing. "
            "Focus the next revision on the skills and projects that directly map to the role."
        )

    return (
        "Low match signal. The resume is missing too many role-specific keywords, so the strongest next step is "
        "to add targeted projects, skills, and evidence that align with the job description."
    )


def _build_gemini_prompt(
    *,
    resume_filename: str,
    job_description_filename: str,
    ats_score: int,
    matched_keywords: list[str],
    missing_keywords: list[str],
    retrieved_context: list[str],
    resume_sections: dict[str, str],
    job_sections: dict[str, str],
) -> str:
    return dedent(
        f"""
        You are Gemini acting as a resume analysis agent inside a multi-step pipeline.

        Return valid JSON only with these keys:
        - ats_score: integer 0-100
        - strengths: array of short strings
        - weaknesses: array of short strings
        - suggestions: array of short strings
        - interview_questions: array of short strings
        - learning_roadmap: array of short strings
        - recruiter_feedback: string

        Context:
        - resume_filename: {resume_filename}
        - job_description_filename: {job_description_filename}
        - baseline_ats_score: {ats_score}
        - matched_keywords: {matched_keywords}
        - missing_keywords: {missing_keywords}
        - resume_sections: {resume_sections}
        - job_sections: {job_sections}
        - retrieved_context: {retrieved_context}

        Instructions:
        - Use the retrieved resume and JD chunks to produce recruiter-style analysis.
        - Keep suggestions concrete and aligned to ATS and hiring feedback.
        - If the score needs adjustment, return a more defensible ATS score.
        - Do not include markdown fences, commentary, or explanations outside JSON.
        """
    ).strip()


def run_agent_pipeline(
    *,
    resume_text: str,
    job_description_text: str,
    resume_filename: str,
    job_description_filename: str,
) -> AnalysisResponse:
    resume_chunks = split_text_into_chunks(resume_text, source="resume")
    job_description_chunks = split_text_into_chunks(job_description_text, source="job_description")
    all_chunks = resume_chunks + job_description_chunks

    agent_trace = [
        f"Resume Parser Agent: {len(resume_chunks)} chunks extracted from {resume_filename}.",
        f"JD Analyzer Agent: {len(job_description_chunks)} chunks extracted from {job_description_filename}.",
    ]

    if all_chunks:
        vector_store = LocalVectorStore(all_chunks)
        resume_context = vector_store.search("resume experience skills projects achievements", top_k=5, source="resume")
        job_context = vector_store.search(
            "job description requirements qualifications responsibilities skills", top_k=5, source="job_description"
        )
        analysis_context = vector_store.search(
            "ATS score missing skills strengths weaknesses suggestions interview questions learning roadmap",
            top_k=8,
        )
    else:
        resume_context = []
        job_context = []
        analysis_context = []

    resume_signal = "\n".join(chunk.chunk.text for chunk in resume_context) or resume_text
    job_signal = "\n".join(chunk.chunk.text for chunk in job_context) or job_description_text

    resume_sections = _split_by_headings(resume_signal)
    job_sections = _split_by_headings(job_signal)

    resume_keywords = set(_top_keywords(" ".join(resume_sections.values()) or resume_signal, 40))
    job_keywords = _top_keywords(" ".join(job_sections.values()) or job_signal, 40)

    ats_score, matched_keywords, missing_keywords = _score_overlap(resume_keywords, job_keywords)
    agent_trace.extend(
        [
            f"Skill Gap Agent: {len(matched_keywords)} matched keywords and {len(missing_keywords)} missing keywords.",
            f"ATS Scoring Agent: baseline score computed at {ats_score}%.",
        ]
    )

    retrieved_context = [
        f"[{chunk.chunk.source} #{chunk.chunk.index}] {chunk.chunk.text[:240]}" for chunk in analysis_context
    ]
    if not retrieved_context:
        retrieved_context = ["No chunks were available for retrieval."]

    gemini_prompt = _build_gemini_prompt(
        resume_filename=resume_filename,
        job_description_filename=job_description_filename,
        ats_score=ats_score,
        matched_keywords=matched_keywords,
        missing_keywords=missing_keywords,
        retrieved_context=retrieved_context,
        resume_sections=resume_sections,
        job_sections=job_sections,
    )

    gemini_result = generate_gemini_analysis(gemini_prompt)
    gemini_model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

    if gemini_result:
        agent_trace.append(f"Gemini Analysis Agent: generated structured output with model {gemini_model}.")
    else:
        agent_trace.append("Gemini Analysis Agent: unavailable, using local fallback analysis.")

    strengths = gemini_result.get("strengths", []) if gemini_result else []
    weaknesses = gemini_result.get("weaknesses", []) if gemini_result else []
    suggestions = gemini_result.get("suggestions", []) if gemini_result else []
    interview_questions = gemini_result.get("interview_questions", []) if gemini_result else []
    learning_roadmap = gemini_result.get("learning_roadmap", []) if gemini_result else []
    recruiter_feedback = gemini_result.get("recruiter_feedback") if gemini_result else None
    ats_score = int(gemini_result.get("ats_score", ats_score)) if gemini_result else ats_score

    if not strengths:
        strengths = matched_keywords[:5] or ["Resume has some overlap with the job description."]

    if not weaknesses:
        weaknesses = missing_keywords[:5] or ["The resume already covers the most common JD keywords."]

    if not suggestions:
        suggestions = [
            "Add more direct evidence for the missing keywords.",
            "Rewrite bullets to show impact, metrics, and ownership.",
            "Tune the summary section to mirror the role requirements.",
        ]

    if not interview_questions:
        interview_questions = [
            "Can you explain how your experience matches the most important JD requirements?",
            "Which project best demonstrates the missing skills you want to learn next?",
            "How would you improve this resume for ATS readability?",
        ]

    if not learning_roadmap:
        learning_roadmap = (
            [f"Learn or deepen {keyword} through a project, tutorial, or certification." for keyword in missing_keywords[:5]]
            or ["Keep strengthening the skills already present in the resume."]
        )

    agent_trace.append(
        f"Learning Advisor Agent: generated {len(learning_roadmap)} roadmap item(s) from the missing keywords."
    )

    return AnalysisResponse(
        resume_filename=resume_filename,
        job_description_filename=job_description_filename,
        ats_score=ats_score,
        matched_keywords=matched_keywords,
        missing_keywords=missing_keywords,
        retrieved_context=retrieved_context,
        agent_trace=agent_trace,
        strengths=_section_feedback(title="Strengths", items=strengths),
        weaknesses=_section_feedback(title="Weaknesses", items=weaknesses),
        suggestions=_section_feedback(title="Improvement Suggestions", items=suggestions),
        interview_questions=_section_feedback(title="Interview Questions", items=interview_questions),
        learning_roadmap=_section_feedback(title="Learning Roadmap", items=learning_roadmap),
        recruiter_feedback=recruiter_feedback or _build_recruiter_feedback(ats_score, missing_keywords, matched_keywords),
    )
