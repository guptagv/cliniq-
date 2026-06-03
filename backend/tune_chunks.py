"""
Test different chunk sizes to find the best one.
Deletes and rebuilds the vector store for each config.
"""

import shutil
import time
from pdf_loader import load_pdf
from vectorstore import chunk_pages, create_vectorstore
from rag_engine import query_documents

PDF_PATH = "sample_docs/Prot_000.pdf"  # Change to your test PDF
COLLECTION = "tuning_test"

TEST_QUESTIONS = [
    "What is the primary endpoint of this study?",
    "What are the inclusion criteria?",
    "What is the study drug and how is it administered?",
]

CONFIGS = [
    {"chunk_size": 300, "overlap": 75,  "label": "Small (300/75)"},
    {"chunk_size": 500, "overlap": 100, "label": "Medium (500/100)"},
    {"chunk_size": 800, "overlap": 150, "label": "Large (800/150)"},
    {"chunk_size": 500, "overlap": 200, "label": "Medium + High overlap (500/200)"},
]

def test_config(config, pages):
    # Clean old data
    shutil.rmtree("./chroma_db", ignore_errors=True)

    # Chunk and store
    chunks = chunk_pages(pages, chunk_size=config["chunk_size"], overlap=config["overlap"])
    create_vectorstore(chunks, collection_name=COLLECTION)

    print(f"\n--- {config['label']} ---")
    print(f"Total chunks: {len(chunks)}")

    # Test questions
    total_score = 0
    for q in TEST_QUESTIONS:
        result = query_documents(q, collection_name=COLLECTION)
        confidence = result["confidence"]
        score = {"high": 3, "medium": 2, "low": 1}.get(confidence, 0)
        total_score += score
        print(f"  Q: {q[:50]}... → {confidence} ({result['chunks_used']} chunks)")

    print(f"  Total score: {total_score}/{len(TEST_QUESTIONS) * 3}")
    return total_score

if __name__ == "__main__":
    pages = load_pdf(PDF_PATH)
    print(f"Loaded {len(pages)} pages from {PDF_PATH}")

    results = []
    for config in CONFIGS:
        score = test_config(config, pages)
        results.append((config["label"], score))

    print(f"\n{'='*50}")
    print("RESULTS SUMMARY")
    print(f"{'='*50}")
    for label, score in sorted(results, key=lambda x: x[1], reverse=True):
        bar = "█" * score + "░" * (9 - score)
        print(f"  {label:40} {bar} {score}/9")

    # Clean up — rebuild with the best config
    print("\nDone! Update vectorstore.py with the winning chunk_size and overlap.")