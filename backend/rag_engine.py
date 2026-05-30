"""
ClinIQ - Improved RAG Engine
Replace your existing rag_engine.py with this file.

Key improvements:
1. Retrieves more chunks (6 instead of 4) for better coverage
2. Uses section metadata in the context (Claude knows WHERE info came from)
3. Better system prompt tuned for clinical/regulatory documents
4. Filters out low-relevance chunks using similarity score threshold
5. Returns section info alongside page numbers
"""

import os
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

load_dotenv()

embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# ──────────────────────────────────────────────
# SYSTEM PROMPT
# This is the single most important thing for
# answer quality. Tune this as you test.
# ──────────────────────────────────────────────

SYSTEM_PROMPT = """You are ClinIQ, an expert AI assistant for clinical trial documents.
You help pharma professionals — medical writers, biostatisticians, clinical scientists —
find precise information in protocols, SAPs, CSRs, and regulatory documents.

Rules you MUST follow:
1. Answer ONLY from the provided context. Never make up information.
2. ALWAYS cite the page number and section for every fact you state.
   Format: (Page X, Section Name)
3. If the context does not contain enough information to answer fully,
   say exactly what IS available and what is missing.
4. Use precise clinical/regulatory terminology as found in the source.
5. If multiple sections are relevant, synthesize across them but cite each.
6. For inclusion/exclusion criteria, list them exactly as stated — do not summarize.
7. For endpoints, distinguish clearly between primary, secondary, and exploratory.
8. If the question is ambiguous, answer the most likely interpretation and
   briefly note other possible interpretations.
"""


def query_documents(question, collection_name="cliniq_docs", top_k=6, score_threshold=1.5):
    """
    Query the vector store and get an AI-powered answer.

    Args:
        question: The user's question in plain English
        collection_name: Which ChromaDB collection to search
        top_k: Number of chunks to retrieve (6 gives good coverage)
        score_threshold: Max distance score to accept (lower = more relevant)
                        ChromaDB uses L2 distance, so lower is better.
                        1.5 is a reasonable cutoff. Increase if getting too few results.
    """

    # Load existing vector store
    vectorstore = Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory="./chroma_db"
    )

    # Find relevant chunks WITH similarity scores
    results = vectorstore.similarity_search_with_score(question, k=top_k)

    # Filter out low-relevance chunks
    # (ChromaDB L2 distance: 0 = identical, higher = less relevant)
    filtered_results = [
        (doc, score) for doc, score in results
        if score <= score_threshold
    ]

    if not filtered_results:
        return {
            "answer": "I couldn't find relevant information in the uploaded documents to answer this question. Try rephrasing or check if the right document has been uploaded.",
            "pages_cited": [],
            "sections_cited": [],
            "chunks_used": 0,
            "confidence": "low"
        }

    # Build context with page numbers AND section names
    context_parts = []
    pages_cited = set()
    sections_cited = set()

    for doc, score in filtered_results:
        page_num = doc.metadata.get("page_number", "?")
        section = doc.metadata.get("section", "General")
        pages_cited.add(page_num)
        sections_cited.add(section)

        context_parts.append(
            f"[Page {page_num} | Section: {section}]:\n{doc.page_content}"
        )

    context = "\n\n---\n\n".join(context_parts)

    # Determine confidence based on how many good chunks we found
    if len(filtered_results) >= 4:
        confidence = "high"
    elif len(filtered_results) >= 2:
        confidence = "medium"
    else:
        confidence = "low"

    # Ask Claude with enriched context
    llm = ChatAnthropic(
        model="claude-sonnet-4-6",  # Change to claude-opus-4-7 if you want premium
        temperature=0,              # 0 = deterministic, no creativity
        max_tokens=2048,            # Allow longer answers for detailed questions
    )

    prompt = f"""{SYSTEM_PROMPT}

--- DOCUMENT CONTEXT ---
{context}
--- END CONTEXT ---

Question: {question}

Provide a thorough answer with page and section citations."""

    response = llm.invoke(prompt)

    return {
        "answer": response.content,
        "pages_cited": sorted(pages_cited),
        "sections_cited": sorted(sections_cited),
        "chunks_used": len(filtered_results),
        "confidence": confidence
    }


# ──────────────────────────────────────────────
# TEST IT
# ──────────────────────────────────────────────

if __name__ == "__main__":
    # Test with several types of questions
    test_questions = [
        "What is the primary endpoint of this study?",
        "What are the inclusion criteria?",
        "What is the study drug and how is it administered?",
    ]

    for question in test_questions:
        print(f"\n{'=' * 60}")
        print(f"Q: {question}")
        print(f"{'=' * 60}")

        result = query_documents(question)

        print(f"\nAnswer:\n{result['answer']}")
        print(f"\nPages cited: {result['pages_cited']}")
        print(f"Sections: {result['sections_cited']}")
        print(f"Confidence: {result['confidence']}")
        print(f"Chunks used: {result['chunks_used']}")