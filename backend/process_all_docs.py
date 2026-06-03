"""
Process all PDFs in sample_docs/ folder into ChromaDB.
Run this once after adding new PDFs.
"""

import os
from pdf_loader import load_pdf
from vectorstore import chunk_pages, create_vectorstore

DOCS_DIR = "sample_docs"

def process_all():
    pdf_files = [f for f in os.listdir(DOCS_DIR) if f.lower().endswith(".pdf")]
    print(f"Found {len(pdf_files)} PDFs in {DOCS_DIR}/\n")

    for f in pdf_files:
        path = os.path.join(DOCS_DIR, f)
        col_name = f.replace(".pdf", "").replace(" ", "_").lower()

        print(f"Processing: {f}")
        try:
            pages = load_pdf(path)
            chunks = chunk_pages(pages, doc_name=f)
            create_vectorstore(chunks, collection_name=col_name)
            print(f"  Done: {len(pages)} pages, {len(chunks)} chunks\n")
        except Exception as e:
            print(f"  ERROR: {e}\n")

    # Show summary
    import chromadb
    client = chromadb.PersistentClient(path="./chroma_db")
    cols = client.list_collections()
    print(f"\nTotal collections in ChromaDB: {len(cols)}")
    for c in cols:
        print(f"  {c.name} ({c.count()} chunks)")

if __name__ == "__main__":
    process_all()