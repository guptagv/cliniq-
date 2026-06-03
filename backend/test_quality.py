"""
ClinIQ Quality Testing Script
Tests the same 5 questions across multiple documents.
Run this after uploading each document.
"""

import json
import time
from rag_engine import query_documents

TEST_QUESTIONS = [
    "What is the primary endpoint of this study?",
    "What are the inclusion criteria?",
    "What is the study drug and how is it administered?",
    "What is the sample size and how was it calculated?",
    "What safety monitoring is in place?",
]

def test_document(collection_name: str):
    """Run all test questions against a document."""
    print(f"\n{'='*70}")
    print(f"TESTING: {collection_name}")
    print(f"{'='*70}")

    results = []

    for q in TEST_QUESTIONS:
        print(f"\nQ: {q}")
        start = time.time()
        result = query_documents(q, collection_name=collection_name)
        elapsed = time.time() - start

        print(f"Confidence: {result['confidence']}")
        print(f"Pages: {result['pages_cited']}")
        print(f"Sections: {result['sections_cited']}")
        print(f"Time: {elapsed:.1f}s")
        print(f"Answer preview: {result['answer'][:200]}...")

        results.append({
            "question": q,
            "confidence": result["confidence"],
            "pages_cited": result["pages_cited"],
            "sections_cited": result["sections_cited"],
            "chunks_used": result["chunks_used"],
            "time_seconds": round(elapsed, 1),
            "answer_length": len(result["answer"]),
        })

    # Save results
    output_file = f"test_results_{collection_name}.json"
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {output_file}")

    # Summary
    high = sum(1 for r in results if r["confidence"] == "high")
    medium = sum(1 for r in results if r["confidence"] == "medium")
    low = sum(1 for r in results if r["confidence"] == "low")
    print(f"\nSummary: {high} high, {medium} medium, {low} low confidence")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        test_document(sys.argv[1])
    else:
        print("Usage: python test_quality.py <collection_name>")
        print("Example: python test_quality.py prot_000")

        # Or test all collections:
        import chromadb
        client = chromadb.PersistentClient(path="./chroma_db")
        collections = client.list_collections()
        if collections:
            print(f"\nAvailable collections: {[c.name for c in collections]}")
            for c in collections:
                test_document(c.name)
        else:
            print("No documents uploaded yet. Upload some first.")