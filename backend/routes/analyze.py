from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from models.schemas import AnalysisResponse, AnalysisSummary
from services.analysis_service import analyze_documents
from services.auth_service import get_user_by_username
from services.pdf_service import extract_text_from_pdf
from services.history_service import get_analysis, list_recent_analyses, save_analysis
from routes.auth import get_current_username

router = APIRouter(prefix="/api", tags=["analysis"])


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_resume(
    resume: UploadFile = File(...),
    job_description: UploadFile = File(...),
    username: str = Depends(get_current_username),
) -> AnalysisResponse:
    resume_text = await extract_text_from_pdf(resume)
    job_description_text = await extract_text_from_pdf(job_description)

    analysis = analyze_documents(
        resume_text=resume_text,
        job_description_text=job_description_text,
        resume_filename=resume.filename or "resume.pdf",
        job_description_filename=job_description.filename or "job-description.pdf",
    )

    user = get_user_by_username(username)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid user")

    return save_analysis(analysis, user_id=int(user["user_id"]))


@router.get("/analyses", response_model=list[AnalysisSummary])
def get_analyses(limit: int = 10, username: str = Depends(get_current_username)) -> list[AnalysisSummary]:
    user = get_user_by_username(username)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid user")

    return list_recent_analyses(user_id=int(user["user_id"]), limit=limit)


@router.get("/analyses/{analysis_id}", response_model=AnalysisResponse)
def get_analysis_detail(analysis_id: str, username: str = Depends(get_current_username)) -> AnalysisResponse:
    user = get_user_by_username(username)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid user")

    analysis = get_analysis(analysis_id=analysis_id, user_id=int(user["user_id"]))
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")

    return analysis
