# AI Resume Analyzer MVP

FastAPI + React MVP that compares a resume PDF against a job description and returns ATS feedback, missing skills, interview questions, and a learning roadmap.

## Planned Flow

1. Upload resume and job description PDFs.
2. Extract and clean text.
3. Chunk documents and build embeddings.
4. Store chunks in a vector database.
5. Retrieve relevant context for analysis.
6. Generate structured feedback with an LLM.

## Current Scaffold

- `backend/` contains the FastAPI API, PDF extraction, local retrieval, Gemini fallback, and persistence.
- `frontend/` contains the React UI for uploads, results, retrieval context, and analysis history.

## What It Does Now

- Uploads two PDFs and extracts text from both.
- Breaks the documents into chunks and retrieves the most relevant sections.
- Produces ATS scoring, missing keywords, strengths, weaknesses, and roadmap suggestions.
- Saves analysis runs locally so you can revisit them.
- Uses Gemini when configured, otherwise falls back to local analysis.

## What It Is Not Yet

- It is not a full production SaaS.
- It does not yet have user accounts, hosted persistence, or background job processing.
- It is an MVP with a real working pipeline, not a finished commercial product.

## Notes for Reviewers

- The project is intentionally honest about its current scope.
- The UI and README describe the app as an MVP with a real pipeline and local history.
- Dockerfiles are available at [backend/Dockerfile](backend/Dockerfile) and [frontend/Dockerfile](frontend/Dockerfile).
- The frontend image accepts `VITE_API_URL` as a build argument.
- Use the generated plan in [.azure/containerization-plan.copilotmd](.azure/containerization-plan.copilotmd) if you want to continue toward Azure deployment.

## Next Steps

1. Build the FastAPI upload and analysis endpoints.
2. Add the React dashboard for upload and results.
3. Wire in embeddings, FAISS or ChromaDB, and LLM prompts.
4. Add the agent pipeline for parsing, comparison, scoring, and recommendations.
