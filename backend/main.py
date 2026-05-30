import os
import shutil
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pdf_loader import load_pdf
from vectorstore import chunk_pages, create_vectorstore
from rag_engine import query_documents

app = FastAPI(title="ClinIQ API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten this later
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

class QuestionRequest(BaseModel):
    question: str
    collection_name: str = "cliniq_docs"

@app.get("/")
def health_check():
    return {"status": "ClinIQ API is running", "version": "0.1.0"}

@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    pages = load_pdf(file_path)
    chunks = chunk_pages(pages)
    create_vectorstore(chunks)

    return {
        "message": f"Processed {file.filename}",
        "pages": len(pages),
        "chunks": len(chunks)
    }

@app.post("/ask")
async def ask_question(req: QuestionRequest):
    result = query_documents(req.question, req.collection_name)
    return result

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)