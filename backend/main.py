import os
from contextlib import asynccontextmanager

import uvicorn
from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from ingestion import CHROMA_PERSIST_DIRECTORY, PDF_DIRECTORY, ingest_pdfs
from ingestion import (
    collection as chroma_collection,
)
from pydantic import BaseModel
from rag_pipeline import final_rag_chain

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("FastAPI application lifespan: startup sequence beginning.")

    if not PDF_DIRECTORY.exists():
        PDF_DIRECTORY.mkdir(exist_ok=True)
        print(f"Created PDF_DIRECTORY at {PDF_DIRECTORY}")
    if not CHROMA_PERSIST_DIRECTORY.exists():
        CHROMA_PERSIST_DIRECTORY.mkdir(exist_ok=True)
        print(f"Created CHROMA_PERSIST_DIRECTORY at {CHROMA_PERSIST_DIRECTORY}")

    try:
        if not CHROMA_PERSIST_DIRECTORY.exists() or chroma_collection.count() == 0:
            print(
                "WARNING: ChromaDB might be empty or not initialized. "
                "Consider running ingestion or using the /ingest endpoint."
            )
        else:
            print(
                f"ChromaDB collection '{chroma_collection.name}' loaded with {chroma_collection.count()} documents."
            )
    except Exception as e:
        print(
            f"Error checking ChromaDB during startup: {e}. It might not be initialized yet."
        )
        print(
            "Consider running ingestion.py script first or using the /ingest endpoint."
        )

    print("FastAPI application started successfully.")
    yield
    print("FastAPI application lifespan: shutdown sequence.")
    print("FastAPI application shutdown complete.")


app = FastAPI(
    title="Scientific PDF RAG Chat API",
    description="Chat with your scientific PDF documents using Gemini, Langchain, and ChromaDB.",
    lifespan=lifespan,
)

ALLOWED_ORIGINS_STR = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost,http://localhost:8080,http://127.0.0.1,http://127.0.0.1:8080",
)
origins = [origin.strip() for origin in ALLOWED_ORIGINS_STR.split(",")]

IS_DEVELOPMENT = os.getenv("ENVIRONMENT", "development").lower() == "development"
if IS_DEVELOPMENT:
    print("Development mode: Allowing all origins for CORS.")
    origins = ["*"]
else:
    origins = [origin.strip() for origin in ALLOWED_ORIGINS_STR.split(",")]
print(f"Configuring CORS for origins: {origins}")


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=[
        "GET",
        "POST",
        "OPTIONS",
    ],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    query: str


class QueryResponse(BaseModel):
    answer: str


class IngestResponse(BaseModel):
    message: str
    documents_in_collection: int | None = None


@app.post(
    "/ingest",
    response_model=IngestResponse,
    summary="Ingest PDFs from the pdf_documents folder",
)
async def ingest_documents_endpoint(background_tasks: BackgroundTasks):
    print("Received request to start PDF ingestion...")
    if not PDF_DIRECTORY.exists() or not any(PDF_DIRECTORY.glob("*.pdf")):
        return IngestResponse(
            message=f"No PDFs found in {PDF_DIRECTORY} or directory does not exist. Ingestion skipped."
        )

    background_tasks.add_task(ingest_pdfs)

    current_count = 0
    try:
        current_count = chroma_collection.count()
    except Exception as e:
        print(f"Could not get collection count during ingest request: {e}")

    return IngestResponse(
        message="PDF ingestion process started in the background. Check server logs for progress and completion.",
        documents_in_collection=current_count,
    )


@app.post(
    "/chat",
    response_model=QueryResponse,
    summary="Ask a question about the indexed PDFs",
)
async def chat_with_pdfs(request: QueryRequest):
    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    try:
        if chroma_collection.count() == 0:
            raise HTTPException(
                status_code=503,
                detail="Vector database is empty. Please ingest documents first using the /ingest endpoint.",
            )
    except Exception as e:
        print(f"Error checking ChromaDB collection count: {e}")
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable. Database may not be ready. Please try again shortly or ingest documents.",
        )

    try:
        print(f"Received query: '{request.query}'")
        answer = final_rag_chain.invoke(request.query)
        print(f"Generated answer snippet: {answer[:200]}...")
        return QueryResponse(answer=answer)
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error during RAG chain invocation: {e}")
        import traceback

        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail="Error processing your query: An internal server error occurred.",
        )


@app.get("/", summary="Root endpoint to check if API is running")
async def root():
    return {"message": "Scientific PDF RAG Chat API is running!"}


if __name__ == "__main__":
    print("Starting Uvicorn server for main:app...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
