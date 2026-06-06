"""
ClinIQ - Improved Vector Store with Clinical Document-Aware Chunking
Replace your existing vectorstore.py with this file.

Key improvements over the basic version:
1. Section-aware splitting - detects protocol sections (Endpoints, Inclusion/Exclusion, etc.)
2. Smarter chunk sizes - smaller chunks (500 chars) with more overlap (100 chars)
3. Richer metadata - stores section headers, document name, page range
4. Preserves context - keeps section headers attached to their content
"""

import re
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

# Use free local embeddings (no API cost!)
embeddings = HuggingFaceEmbeddings(
    model_name="all-MiniLM-L6-v2"
)

# ──────────────────────────────────────────────
# SECTION DETECTION
# Clinical protocols follow a predictable structure.
# Detecting sections lets us tag each chunk with
# WHERE in the document it came from.
# ──────────────────────────────────────────────

CLINICAL_SECTION_PATTERNS = [
    r"(?i)^\s*\d+\.?\d*\.?\d*\s+(INTRODUCTION|BACKGROUND)",
    r"(?i)^\s*\d+\.?\d*\.?\d*\s+(STUDY\s+OBJECTIVES?|OBJECTIVES?)",
    r"(?i)^\s*\d+\.?\d*\.?\d*\s+(STUDY\s+DESIGN)",
    r"(?i)^\s*\d+\.?\d*\.?\d*\s+(STUDY\s+POPULATION|ELIGIBILITY|SELECTION\s+OF\s+SUBJECTS?)",
    r"(?i)^\s*\d+\.?\d*\.?\d*\s+(INCLUSION\s+CRITERIA)",
    r"(?i)^\s*\d+\.?\d*\.?\d*\s+(EXCLUSION\s+CRITERIA)",
    r"(?i)^\s*\d+\.?\d*\.?\d*\s+(ENDPOINTS?|OUTCOME\s+MEASURES?)",
    r"(?i)^\s*\d+\.?\d*\.?\d*\s+(PRIMARY\s+ENDPOINT|PRIMARY\s+OBJECTIVE)",
    r"(?i)^\s*\d+\.?\d*\.?\d*\s+(SECONDARY\s+ENDPOINT|SECONDARY\s+OBJECTIVE)",
    r"(?i)^\s*\d+\.?\d*\.?\d*\s+(SAFETY|ADVERSE\s+EVENTS?)",
    r"(?i)^\s*\d+\.?\d*\.?\d*\s+(STATISTICAL\s+(METHODS?|ANALYSIS|CONSIDERATIONS?))",
    r"(?i)^\s*\d+\.?\d*\.?\d*\s+(SAMPLE\s+SIZE)",
    r"(?i)^\s*\d+\.?\d*\.?\d*\s+(STUDY\s+PROCEDURES?|SCHEDULE\s+OF\s+(ACTIVITIES|ASSESSMENTS?))",
    r"(?i)^\s*\d+\.?\d*\.?\d*\s+(INVESTIGATIONAL\s+PRODUCT|STUDY\s+(DRUG|INTERVENTION|TREATMENT))",
    r"(?i)^\s*\d+\.?\d*\.?\d*\s+(DOSAGE|DOSE\s+MODIFICATION)",
    r"(?i)^\s*\d+\.?\d*\.?\d*\s+(INFORMED\s+CONSENT|ETHICAL\s+CONSIDERATIONS?|ETHICS)",
    r"(?i)^\s*\d+\.?\d*\.?\d*\s+(REFERENCES?|BIBLIOGRAPHY)",
    r"(?i)^\s*\d+\.?\d*\.?\d*\s+(APPENDIX|APPENDICES)",
    r"(?i)^\s*\d+\.?\d*\.?\d*\s+(ABBREVIATIONS?|DEFINITIONS?|GLOSSARY)",
    r"(?i)^\s*\d+\.?\d*\.?\d*\s+(DISCONTINUATION|WITHDRAWAL|DROPOUT)",
    r"(?i)^\s*\d+\.?\d*\.?\d*\s+(DATA\s+MANAGEMENT|DATA\s+COLLECTION)",
]


def detect_section(text):
    """
    Look at the first few lines of a chunk and try to
    identify which protocol section it belongs to.
    Returns the section name or "General" if not detected.
    """
    # Check first 200 chars for section headers
    header_area = text[:200]
    for pattern in CLINICAL_SECTION_PATTERNS:
        match = re.search(pattern, header_area)
        if match:
            # Clean up the matched section name
            section = match.group(1).strip().title()
            return section
    return "General"


# ──────────────────────────────────────────────
# IMPROVED CHUNKING
# ──────────────────────────────────────────────

def chunk_pages(pages, chunk_size=500, overlap=100, doc_name="unknown"):
    """
    Split pages into chunks with rich metadata.

    Why 500 chars instead of 1000?
    - Clinical documents are dense. A 500-char chunk usually
      contains one complete thought (one criterion, one endpoint).
    - Smaller chunks = more precise retrieval.
    - We retrieve 4-6 chunks anyway, so total context is still large.

    Why 100 char overlap?
    - Ensures sentences aren't cut in half at boundaries.
    - A sentence that starts at the end of chunk A also appears
      at the start of chunk B.
    """

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        # Split on these separators IN ORDER of priority.
        # This keeps paragraphs together, then sentences,
        # and only splits mid-sentence as a last resort.
        separators=[
            "\n\n",      # Double newline = paragraph break (best split)
            "\n",        # Single newline = line break
            ". ",        # Period + space = end of sentence
            "; ",        # Semicolon = clause break
            ", ",        # Comma = phrase break (less ideal)
            " ",         # Space = word break (last resort)
        ],
        length_function=len,
    )

    chunks = []
    current_section = "General"

    for page in pages:
        text = page["content"]
        page_num = page["page_number"]

        # Check if this page starts a new section
        detected = detect_section(text)
        if detected != "General":
            current_section = detected

        # Split this page's text
        page_chunks = splitter.split_text(text)

        for i, chunk_text in enumerate(page_chunks):
            # Skip very short chunks (headers, page numbers, etc.)
            if len(chunk_text.strip()) < 50:
                continue
            # Skip table of contents lines (mostly dots and page numbers)
            if chunk_text.count('.') > len(chunk_text) * 0.3:
                continue
            if chunk_text.count('...') > 3:
                continue

            # Check if THIS chunk starts a new section
            chunk_section = detect_section(chunk_text)
            if chunk_section != "General":
                current_section = chunk_section

            chunks.append({
                "content": chunk_text,
                "page_number": page_num,
                "section": current_section,
                "doc_name": doc_name,
                "chunk_index": len(chunks),  # Global position
            })

    return chunks


# ──────────────────────────────────────────────
# VECTOR STORE CREATION
# ──────────────────────────────────────────────

def create_vectorstore(chunks, collection_name="cliniq_docs"):
    """
    Store chunks in ChromaDB with all metadata.

    The metadata is what makes retrieval powerful:
    - page_number: for citations ("Answer found on page 12")
    - section: for filtered search ("search only in Endpoints")
    - doc_name: for multi-document support later
    """

    texts = [c["content"] for c in chunks]
    metadatas = [
        {
            "page_number": c["page_number"],
            "section": c["section"],
            "doc_name": c["doc_name"],
            "chunk_index": c["chunk_index"],
        }
        for c in chunks
    ]

    vectorstore = Chroma.from_texts(
        texts=texts,
        metadatas=metadatas,
        embedding=embeddings,
        collection_name=collection_name,
        persist_directory="./chroma_db"
    )

    print(f"Stored {len(chunks)} chunks in collection '{collection_name}'")

    # Print a summary of sections found
    sections = set(c["section"] for c in chunks)
    print(f"Sections detected: {', '.join(sorted(sections))}")

    return vectorstore


# ──────────────────────────────────────────────
# TEST IT
# ──────────────────────────────────────────────

if __name__ == "__main__":
    from pdf_loader import load_pdf

    # Change this to your PDF filename
    pdf_path = "sample_docs/Prot_000-1.pdf"
    doc_name = pdf_path.split("/")[-1].replace(".pdf", "")

    print(f"Loading: {pdf_path}")
    pages = load_pdf(pdf_path)
    print(f"Loaded {len(pages)} pages")

    print(f"\nChunking with section detection...")
    chunks = chunk_pages(pages, doc_name=doc_name)
    print(f"Created {len(chunks)} chunks")

    # Show a few sample chunks so you can verify quality
    print("\n" + "=" * 60)
    print("SAMPLE CHUNKS (first 3)")
    print("=" * 60)
    for c in chunks[:3]:
        print(f"\n--- Chunk {c['chunk_index']} | Page {c['page_number']} | Section: {c['section']} ---")
        print(c["content"][:200] + "...")

    print("\n\nCreating vector store...")
    vectorstore = create_vectorstore(chunks)
    print("Done!")
