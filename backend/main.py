"""
ClinIQ Backend - main.py (Day 28)

All features:
- User-scoped documents (each user's docs are isolated)
- Multi-document support with collections
- Cross-document queries via /ask-all
- Rate limiting (30 questions per hour per user)
- File validation (PDF only, max 10MB)
- CORS restricted to known origins
- Health check, list, delete endpoints
"""

import os
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pdf_loader import load_pdf
from vectorstore import chunk_pages, create_vectorstore
from rag_engine import query_documents, query_all_documents
from rate_limiter import limiter

app = FastAPI(title="ClinIQ API", version="0.3.0")

# CORS - only allow your frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        # Add your Vercel deployment URL here when you deploy:
        # "https://cliniq.vercel.app",
    ],
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


# ──────────────────────────────────────────────
# REQUEST MODELS
# ──────────────────────────────────────────────

class QuestionRequest(BaseModel):
    question: str
    collection_name: str = ""
    user_id: str = "anonymous"


# ──────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────

def make_safe_user(user_id: str) -> str:
    """Convert email to safe collection prefix."""
    return user_id.replace("@", "_at_").replace(".", "_")


# ──────────────────────────────────────────────
# HEALTH & STATUS
# ──────────────────────────────────────────────

@app.get("/")
def root():
    return {"status": "ClinIQ API is running", "version": "0.3.0"}


@app.get("/health")
def health_check():
    try:
        import chromadb
        client = chromadb.PersistentClient(path="./chroma_db")
        collections = client.list_collections()
        return {
            "status": "running",
            "documents_loaded": len(collections),
            "collections": [
                {"name": c.name, "count": c.count()}
                for c in collections
            ]
        }
    except Exception:
        return {"status": "running", "documents_loaded": 0, "collections": []}


# ──────────────────────────────────────────────
# DOCUMENT MANAGEMENT
# ──────────────────────────────────────────────

@app.get("/documents")
def list_documents(user_id: str = "anonymous"):
    """List documents belonging to a specific user only."""
    try:
        import chromadb
        client = chromadb.PersistentClient(path="./chroma_db")
        collections = client.list_collections()

        safe_user = make_safe_user(user_id)
        prefix = f"{safe_user}__"

        user_docs = []
        for c in collections:
            if c.name.startswith(prefix):
                # display_name = the part after the user prefix
                display_name = c.name.split("__", 1)[-1] if "__" in c.name else c.name
                user_docs.append({
                    "name": c.name,
                    "display_name": display_name,
                    "chunks": c.count()
                })

        return {"documents": user_docs}
    except Exception:
        return {"documents": []}


@app.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    user_id: str = Form("anonymous")
):
    """Upload and process a PDF, scoped to the user."""
    # Validate file type
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    # Validate size (10MB limit)
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="File too large. Maximum size is 10MB."
        )
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="File is empty.")

    # Save file
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as f:
        f.write(contents)

    # User-scoped collection name: {safe_user}__{doc_name}
    safe_user = make_safe_user(user_id)
    doc_name = file.filename.replace(".pdf", "").replace(" ", "_").lower()
    collection_name = f"{safe_user}__{doc_name}"

    # Process
    pages = load_pdf(file_path)
    chunks = chunk_pages(pages, doc_name=file.filename)
    create_vectorstore(chunks, collection_name=collection_name)

    return {
        "message": f"Processed {file.filename}",
        "collection_name": collection_name,
        "pages": len(pages),
        "chunks": len(chunks)
    }


@app.delete("/documents/{collection_name}")
def delete_document(collection_name: str, user_id: str = "anonymous"):
    """Delete a document - only if it belongs to this user."""
    safe_user = make_safe_user(user_id)
    # Security: user can only delete THEIR own documents
    if not collection_name.startswith(f"{safe_user}__"):
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to delete this document"
        )

    try:
        import chromadb
        client = chromadb.PersistentClient(path="./chroma_db")
        client.delete_collection(collection_name)
        return {"message": f"Deleted {collection_name}"}
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Document not found: {str(e)}")


# ──────────────────────────────────────────────
# QUERY ENDPOINTS (with rate limiting)
# ──────────────────────────────────────────────

@app.post("/ask")
async def ask_question(req: QuestionRequest):
    """Ask a question about a single document."""
    # Rate limit check
    if not limiter.is_allowed(req.user_id):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Maximum 30 questions per hour. Try again later."
        )

    # Verify the user owns this collection
    safe_user = make_safe_user(req.user_id)

    # If no collection specified, find the first one for this user
    if not req.collection_name:
        import chromadb
        client = chromadb.PersistentClient(path="./chroma_db")
        collections = client.list_collections()
        user_collections = [
            c for c in collections
            if c.name.startswith(f"{safe_user}__")
        ]
        if not user_collections:
            raise HTTPException(status_code=400, detail="No documents uploaded yet")
        req.collection_name = user_collections[0].name

    # Security: prevent users from querying other users' documents
    if not req.collection_name.startswith(f"{safe_user}__"):
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to query this document"
        )

    result = query_documents(req.question, req.collection_name)

    # Include remaining rate limit info
    result["rate_limit_remaining"] = limiter.remaining(req.user_id)
    return result


@app.post("/ask-all")
async def ask_all_documents(req: QuestionRequest):
    """Ask a question across ALL documents belonging to the user."""
    # Rate limit check (cross-doc costs slightly more, but same limit)
    if not limiter.is_allowed(req.user_id):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Maximum 30 questions per hour. Try again later."
        )

    # We need to filter query_all_documents to only search this user's docs
    # Easiest way: temporarily filter at the rag_engine level by passing user_id
    result = query_all_documents_for_user(req.question, req.user_id)
    result["rate_limit_remaining"] = limiter.remaining(req.user_id)
    return result


def query_all_documents_for_user(question: str, user_id: str):
    """Cross-document query, scoped to a single user's documents."""
    import chromadb
    from langchain_chroma import Chroma
    from rag_engine import embeddings, get_confidence, parse_follow_ups, CROSS_DOC_PROMPT
    from langchain_anthropic import ChatAnthropic

    safe_user = make_safe_user(user_id)
    prefix = f"{safe_user}__"

    try:
        client = chromadb.PersistentClient(path="./chroma_db")
        collections = client.list_collections()
    except Exception:
        return {
            "answer": "Error accessing the document database.",
            "pages_cited": [], "sections_cited": [],
            "chunks_used": 0, "confidence": "low",
            "follow_up_questions": [], "documents_searched": []
        }

    # Only search THIS user's collections
    user_collections = [c for c in collections if c.name.startswith(prefix)]

    if not user_collections:
        return {
            "answer": "You haven't uploaded any documents yet.",
            "pages_cited": [], "sections_cited": [],
            "chunks_used": 0, "confidence": "low",
            "follow_up_questions": [], "documents_searched": []
        }

    all_results = []
    docs_searched = []
    score_threshold = 1.5

    for collection in user_collections:
        try:
            if collection.count() == 0:
                continue

            vectorstore = Chroma(
                collection_name=collection.name,
                embedding_function=embeddings,
                persist_directory="./chroma_db"
            )
            results = vectorstore.similarity_search_with_score(question, k=5)

            # Use display_name in citations (without user prefix)
            display_name = collection.name.split("__", 1)[-1]

            for doc, score in results:
                if score <= score_threshold:
                    doc.metadata["source_collection"] = display_name
                    all_results.append((doc, score))

            docs_searched.append(display_name)
        except Exception as e:
            print(f"Skipping collection {collection.name}: {e}")
            continue

    all_results.sort(key=lambda x: x[1])
    all_results = all_results[:20]

    if not all_results:
        return {
            "answer": "I couldn't find relevant information across your documents.",
            "pages_cited": [], "sections_cited": [],
            "chunks_used": 0, "confidence": "low",
            "follow_up_questions": [], "documents_searched": docs_searched
        }

    context_parts = []
    pages_cited = set()
    sections_cited = set()

    for doc, score in all_results:
        page_num = doc.metadata.get("page_number", "?")
        section = doc.metadata.get("section", "General")
        source = doc.metadata.get("source_collection", "unknown")
        pages_cited.add(page_num)
        sections_cited.add(section)
        context_parts.append(
            f"[Document: {source} | Page {page_num} | Section: {section}]:\n{doc.page_content}"
        )

    context = "\n\n---\n\n".join(context_parts)
    confidence = get_confidence(len(all_results))

    llm = ChatAnthropic(
        model="claude-sonnet-4-6",
        temperature=0,
        max_tokens=4096,
    )

    prompt = f"""{CROSS_DOC_PROMPT}

--- DOCUMENT CONTEXT (from {len(docs_searched)} documents) ---
{context}
--- END CONTEXT ---

Question: {question}

Provide a thorough answer organized by document with citations."""

    response = llm.invoke(prompt)
    answer_text, follow_ups = parse_follow_ups(response.content)

    return {
        "answer": answer_text,
        "pages_cited": sorted(pages_cited),
        "sections_cited": sorted(sections_cited),
        "chunks_used": len(all_results),
        "confidence": confidence,
        "follow_up_questions": follow_ups,
        "documents_searched": docs_searched
    }


# ──────────────────────────────────────────────
# RUN SERVER
# ──────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)