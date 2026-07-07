from fastapi import APIRouter, File, HTTPException, UploadFile

from models.schemas import AnalysisResponse, AnalysisSummary
from services.analysis_service import analyze_documents
from services.pdf_service import extract_text_from_pdf
from services.history_service import get_analysis, list_recent_analyses, save_analysis

router = APIRouter(prefix="/api", tags=["analysis"])


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_resume(
    resume: UploadFile = File(...),
    job_description: UploadFile = File(...),
) -> AnalysisResponse:
    resume_text = await extract_text_from_pdf(resume)
    job_description_text = await extract_text_from_pdf(job_description)

    analysis = analyze_documents(
        resume_text=resume_text,
        job_description_text=job_description_text,
        resume_filename=resume.filename or "resume.pdf",
        job_description_filename=job_description.filename or "job-description.pdf",
    )

    return save_analysis(analysis)


@router.get("/analyses", response_model=list[AnalysisSummary])
def get_analyses(limit: int = 10) -> list[AnalysisSummary]:
    return list_recent_analyses(limit=limit)


@router.get("/analyses/{analysis_id}", response_model=AnalysisResponse)
def get_analysis_detail(analysis_id: str) -> AnalysisResponse:
    analysis = get_analysis(analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")

    return analysis
