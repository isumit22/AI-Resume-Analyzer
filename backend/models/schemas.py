from pydantic import BaseModel, Field


class SectionFeedback(BaseModel):
    title: str
    items: list[str] = Field(default_factory=list)


class AnalysisResponse(BaseModel):
    analysis_id: str | None = None
    created_at: str | None = None
    resume_filename: str
    job_description_filename: str
    ats_score: int
    matched_keywords: list[str]
    missing_keywords: list[str]
    retrieved_context: list[str] = Field(default_factory=list)
    agent_trace: list[str] = Field(default_factory=list)
    strengths: SectionFeedback
    weaknesses: SectionFeedback
    suggestions: SectionFeedback
    interview_questions: SectionFeedback
    learning_roadmap: SectionFeedback
    recruiter_feedback: str


class AnalysisSummary(BaseModel):
    analysis_id: str
    created_at: str
    resume_filename: str
    job_description_filename: str
    ats_score: int
    matched_count: int
    missing_count: int


class LoginRequest(BaseModel):
    username: str
    password: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str


class CurrentUserResponse(BaseModel):
    username: str

