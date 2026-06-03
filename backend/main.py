import os
import shutil
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pdf_loader import load_pdf
from vectorstore import chunk_pages, create_vectorstore
from rag_engine import query_documents

app = FastAPI(title="ClinIQ API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)


class QuestionRequest(BaseModel):
    question: str
    collection_name: str = ""  # Empty = search default


@app.get("/")
def root():
    return {"status": "ClinIQ API is running", "version": "0.2.0"}


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


@app.get("/documents")
def list_documents():
    """List all uploaded documents with their chunk counts."""
    try:
        import chromadb
        client = chromadb.PersistentClient(path="./chroma_db")
        collections = client.list_collections()
        return {
            "documents": [
                {"name": c.name, "chunks": c.count()}
                for c in collections
            ]
        }
    except Exception:
        return {"documents": []}


@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    # Validate file type
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    # Read and validate size
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 10MB.")

    # Save file
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as f:
        f.write(contents)

    # Each document gets its own collection
    collection_name = file.filename.replace(".pdf", "").replace(" ", "_").lower()

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


@app.post("/ask")
async def ask_question(req: QuestionRequest):
    # If no collection specified, try to find one
    if not req.collection_name:
        import chromadb
        client = chromadb.PersistentClient(path="./chroma_db")
        collections = client.list_collections()
        if not collections:
            raise HTTPException(status_code=400, detail="No documents uploaded yet")
        req.collection_name = collections[0].name

    result = query_documents(req.question, req.collection_name)
    return result


@app.delete("/documents/{collection_name}")
def delete_document(collection_name: str):
    """Delete a document collection."""
    try:
        import chromadb
        client = chromadb.PersistentClient(path="./chroma_db")
        client.delete_collection(collection_name)
        return {"message": f"Deleted {collection_name}"}
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Document not found: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
@app.post("/ask-all")
async def ask_all_documents(req: QuestionRequest):
    """Ask a question across ALL uploaded documents."""
    from rag_engine import query_all_documents
    result = query_all_documents(req.question)
    return result