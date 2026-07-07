from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.analyze import router as analyze_router
from services.history_service import initialize_history_store

app = FastAPI(title="AI Resume Analyzer", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze_router)


@app.on_event("startup")
def startup_event() -> None:
    initialize_history_store()


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
