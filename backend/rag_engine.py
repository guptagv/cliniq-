"""
ClinIQ - RAG Engine v4
Complete rewrite with all fixes applied.

Features:
- Single document and cross-document queries
- Section-aware citations (page + section)
- Follow-up question suggestions
- Handles abbreviations and tables
- Skips empty/broken collections in cross-doc search
- Uses langchain-chroma (not deprecated langchain_community)
"""

import os
import re
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

load_dotenv()

embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")


# ──────────────────────────────────────────────
# SYSTEM PROMPTS
# ──────────────────────────────────────────────

SINGLE_DOC_PROMPT = """You are ClinIQ, an expert AI assistant for clinical trial documents.
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
9. If an abbreviation is used in the context, spell it out on first use.
   Example: "OS (Overall Survival)"
10. If the context contains tabular data, present it in a structured format.
11. Present all information found in the context completely.
    Do not add warnings about potentially missing information
    unless the context explicitly references content not provided.

After your answer, suggest 2-3 follow-up questions the user might want to ask
based on what you found in the context. Format them exactly like this:

FOLLOW_UP_QUESTIONS:
1. [question]
2. [question]
3. [question]
"""

CROSS_DOC_PROMPT = """You are ClinIQ, an expert AI assistant for clinical trial documents.
The context below comes from MULTIPLE clinical trial documents.

Rules you MUST follow:
1. Answer ONLY from the provided context. Never make up information.
2. For EVERY fact, cite the document name, page number, and section.
   Format: (Document: name, Page X, Section Name)
3. When comparing across documents, clearly organize by document.
4. Use precise clinical/regulatory terminology as found in the source.
5. If an abbreviation is used, spell it out on first use.
6. If some documents don't contain relevant information, say so for those
   specific documents rather than giving a generic warning.
7. Present all information found in the context completely.

After your answer, suggest 2-3 follow-up questions.
Format them exactly like this:

FOLLOW_UP_QUESTIONS:
1. [question]
2. [question]
3. [question]
"""


# ──────────────────────────────────────────────
# HELPER: Parse follow-up questions from response
# ──────────────────────────────────────────────

def parse_follow_ups(full_answer):
    """
    Split Claude's response into the answer and follow-up questions.
    Returns (answer_text, list_of_follow_ups)
    """
    follow_ups = []
    answer_text = full_answer

    if "FOLLOW_UP_QUESTIONS:" in full_answer:
        parts = full_answer.split("FOLLOW_UP_QUESTIONS:")
        answer_text = parts[0].strip()
        follow_up_text = parts[1].strip()

        for line in follow_up_text.split("\n"):
            line = line.strip()
            match = re.match(r'^\d+\.\s*(.+)', line)
            if match:
                follow_ups.append(match.group(1).strip())

    return answer_text, follow_ups[:3]


# ──────────────────────────────────────────────
# HELPER: Calculate confidence
# ──────────────────────────────────────────────

def get_confidence(num_results):
    if num_results >= 4:
        return "high"
    elif num_results >= 2:
        return "medium"
    else:
        return "low"


# ──────────────────────────────────────────────
# SINGLE DOCUMENT QUERY
# ──────────────────────────────────────────────

def query_documents(question, collection_name="cliniq_docs", top_k=10, score_threshold=1.5):
    """
    Query a single document collection and get an AI-powered answer.

    Args:
        question: The user's question in plain English
        collection_name: Which ChromaDB collection to search
        top_k: Number of chunks to retrieve
        score_threshold: Max distance score to accept (lower = more relevant)
    """

    try:
        vectorstore = Chroma(
            collection_name=collection_name,
            embedding_function=embeddings,
            persist_directory="./chroma_db"
        )
    except Exception as e:
        return {
            "answer": f"Error loading document collection '{collection_name}'. It may be corrupted. Try re-uploading the document.",
            "pages_cited": [],
            "sections_cited": [],
            "chunks_used": 0,
            "confidence": "low",
            "follow_up_questions": []
        }

    # Find relevant chunks with similarity scores
    try:
        results = vectorstore.similarity_search_with_score(question, k=top_k)
    except Exception as e:
        return {
            "answer": f"Error searching document. The collection may be empty or corrupted. Try re-uploading.",
            "pages_cited": [],
            "sections_cited": [],
            "chunks_used": 0,
            "confidence": "low",
            "follow_up_questions": []
        }

    # Filter out low-relevance chunks
    filtered_results = [
        (doc, score) for doc, score in results
        if score <= score_threshold
    ]

    if not filtered_results:
        return {
            "answer": "I couldn't find relevant information in the uploaded document to answer this question. Try rephrasing your question or check if the right document has been uploaded.",
            "pages_cited": [],
            "sections_cited": [],
            "chunks_used": 0,
            "confidence": "low",
            "follow_up_questions": []
        }

    # Build context with page numbers and section names
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
    confidence = get_confidence(len(filtered_results))

    # Call Claude
    llm = ChatAnthropic(
        model="claude-sonnet-4-6",
        temperature=0,
        max_tokens=2048,
    )

    prompt = f"""{SINGLE_DOC_PROMPT}

--- DOCUMENT CONTEXT ---
{context}
--- END CONTEXT ---

Question: {question}

Provide a thorough answer with page and section citations, then suggest follow-up questions."""

    response = llm.invoke(prompt)
    answer_text, follow_ups = parse_follow_ups(response.content)

    return {
        "answer": answer_text,
        "pages_cited": sorted(pages_cited),
        "sections_cited": sorted(sections_cited),
        "chunks_used": len(filtered_results),
        "confidence": confidence,
        "follow_up_questions": follow_ups
    }


# ──────────────────────────────────────────────
# CROSS-DOCUMENT QUERY (ALL DOCUMENTS)
# ──────────────────────────────────────────────

def query_all_documents(question, top_k=20, score_threshold=1.5):
    """
    Query across ALL uploaded documents and synthesize an answer.
    Each document gets up to 5 chunks, then the best ones are selected.
    """
    import chromadb

    try:
        client = chromadb.PersistentClient(path="./chroma_db")
        collections = client.list_collections()
    except Exception:
        return {
            "answer": "Error accessing the document database.",
            "pages_cited": [],
            "sections_cited": [],
            "chunks_used": 0,
            "confidence": "low",
            "follow_up_questions": [],
            "documents_searched": []
        }

    if not collections:
        return {
            "answer": "No documents uploaded yet.",
            "pages_cited": [],
            "sections_cited": [],
            "chunks_used": 0,
            "confidence": "low",
            "follow_up_questions": [],
            "documents_searched": []
        }

    # Search across all collections
    all_results = []
    docs_searched = []

    for collection in collections:
        try:
            # Skip empty collections
            if collection.count() == 0:
                print(f"Skipping empty collection: {collection.name}")
                continue

            vectorstore = Chroma(
                collection_name=collection.name,
                embedding_function=embeddings,
                persist_directory="./chroma_db"
            )

            # Get up to 5 chunks per document
            results = vectorstore.similarity_search_with_score(question, k=5)

            for doc, score in results:
                if score <= score_threshold:
                    doc.metadata["source_collection"] = collection.name
                    all_results.append((doc, score))

            docs_searched.append(collection.name)

        except Exception as e:
            print(f"Skipping collection {collection.name}: {e}")
            continue

    # Sort by relevance (lower score = more relevant) and take top results
    all_results.sort(key=lambda x: x[1])
    all_results = all_results[:top_k]

    if not all_results:
        return {
            "answer": "I couldn't find relevant information across any uploaded documents for this question.",
            "pages_cited": [],
            "sections_cited": [],
            "chunks_used": 0,
            "confidence": "low",
            "follow_up_questions": [],
            "documents_searched": docs_searched
        }

    # Build context with document source, page numbers, and section names
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

    # Call Claude with cross-document prompt
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

Provide a thorough answer organized by document with citations, then suggest follow-up questions."""

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
# TEST IT
# ──────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("ClinIQ RAG Engine v4 - Test")
    print("=" * 60)

    # Check what collections exist
    import chromadb
    client = chromadb.PersistentClient(path="./chroma_db")
    collections = client.list_collections()
    print(f"\nFound {len(collections)} collections:")
    for c in collections:
        try:
            count = c.count()
            print(f"  {c.name}: {count} chunks")
        except Exception as e:
            print(f"  {c.name}: ERROR - {e}")

    if not collections:
        print("\nNo documents found. Upload some first.")
        exit()

    # Test single document query
    first_col = collections[0].name
    print(f"\n--- Single Document Query ({first_col}) ---")
    result = query_documents("What is the primary endpoint?", collection_name=first_col)
    print(f"Answer: {result['answer'][:300]}...")
    print(f"Pages: {result['pages_cited']}")
    print(f"Sections: {result['sections_cited']}")
    print(f"Confidence: {result['confidence']}")
    if result['follow_up_questions']:
        print(f"Follow-ups: {result['follow_up_questions']}")

    # Test cross-document query if multiple collections
    if len(collections) > 1:
        print(f"\n--- Cross-Document Query (all {len(collections)} docs) ---")
        result = query_all_documents("What is the primary endpoint of each study?")
        print(f"Answer: {result['answer'][:500]}...")
        print(f"Documents searched: {result['documents_searched']}")
        print(f"Confidence: {result['confidence']}")
        if result['follow_up_questions']:
            print(f"Follow-ups: {result['follow_up_questions']}")