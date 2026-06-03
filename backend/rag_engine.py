"""
ClinIQ - RAG Engine v3
Improvements:
- Better system prompt for clinical documents
- Follow-up question suggestions
- Handles abbreviations and tables
"""

import os
import re
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

load_dotenv()

embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

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


def query_documents(question, collection_name="cliniq_docs", top_k=10, score_threshold=1.5):
    """
    Query the vector store and get an AI-powered answer with follow-ups.
    """

    vectorstore = Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory="./chroma_db"
    )

    results = vectorstore.similarity_search_with_score(question, k=top_k)

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
            "confidence": "low",
            "follow_up_questions": []
        }

    # Build context
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

    # Confidence
    if len(filtered_results) >= 4:
        confidence = "high"
    elif len(filtered_results) >= 2:
        confidence = "medium"
    else:
        confidence = "low"

    # Call Claude
    llm = ChatAnthropic(
        model="claude-sonnet-4-6",
        temperature=0,
        max_tokens=2048,
    )

    prompt = f"""{SYSTEM_PROMPT}

--- DOCUMENT CONTEXT ---
{context}
--- END CONTEXT ---

Question: {question}

Provide a thorough answer with page and section citations, then suggest follow-up questions."""

    response = llm.invoke(prompt)
    full_answer = response.content

    # Parse follow-up questions from the response
    follow_ups = []
    answer_text = full_answer

    if "FOLLOW_UP_QUESTIONS:" in full_answer:
        parts = full_answer.split("FOLLOW_UP_QUESTIONS:")
        answer_text = parts[0].strip()
        follow_up_text = parts[1].strip()

        # Extract numbered questions
        for line in follow_up_text.split("\n"):
            line = line.strip()
            # Match lines like "1. What is..." or "2. How does..."
            match = re.match(r'^\d+\.\s*(.+)', line)
            if match:
                follow_ups.append(match.group(1).strip())

    return {
        "answer": answer_text,
        "pages_cited": sorted(pages_cited),
        "sections_cited": sorted(sections_cited),
        "chunks_used": len(filtered_results),
        "confidence": confidence,
        "follow_up_questions": follow_ups[:3]  # Max 3
    }


if __name__ == "__main__":
    test_questions = [
        "What is the primary endpoint of this study?",
        "What are the inclusion criteria?",
        "What is the study drug and how is it administered?",
    ]

    for question in test_questions:
        print(f"\n{'='*60}")
        print(f"Q: {question}")
        print(f"{'='*60}")

        result = query_documents(question)

        print(f"\nAnswer:\n{result['answer']}")
        print(f"\nPages cited: {result['pages_cited']}")
        print(f"Sections: {result['sections_cited']}")
        print(f"Confidence: {result['confidence']}")

        if result["follow_up_questions"]:
            print(f"\nSuggested follow-ups:")
            for i, q in enumerate(result["follow_up_questions"], 1):
                print(f"  {i}. {q}")
def query_all_documents(question, top_k=10, score_threshold=1.5):
    """Query across ALL uploaded documents and synthesize."""
    import chromadb

    client = chromadb.PersistentClient(path="./chroma_db")
    collections = client.list_collections()

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
        vectorstore = Chroma(
            collection_name=collection.name,
            embedding_function=embeddings,
            persist_directory="./chroma_db"
        )
        results = vectorstore.similarity_search_with_score(question, k=top_k // len(collections) + 1)
        for doc, score in results:
            if score <= score_threshold:
                doc.metadata["source_collection"] = collection.name
                all_results.append((doc, score))
        docs_searched.append(collection.name)

    # Sort by relevance (lower score = more relevant)
    all_results.sort(key=lambda x: x[1])
    all_results = all_results[:top_k]

    if not all_results:
        return {
            "answer": "I couldn't find relevant information across any uploaded documents.",
            "pages_cited": [],
            "sections_cited": [],
            "chunks_used": 0,
            "confidence": "low",
            "follow_up_questions": [],
            "documents_searched": docs_searched
        }

    # Build context with document source
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

    confidence = "high" if len(all_results) >= 4 else "medium" if len(all_results) >= 2 else "low"

    llm = ChatAnthropic(
        model="claude-sonnet-4-6",
        temperature=0,
        max_tokens=2048,
    )

    cross_doc_prompt = """You are ClinIQ, an expert AI assistant for clinical trial documents.
The context below comes from MULTIPLE documents.
For each fact, cite the document name, page number, and section.
Format citations as: (Document: name, Page X, Section Name)
If comparing across documents, clearly indicate which information comes from which document.

After your answer, suggest 2-3 follow-up questions.
Format them exactly like this:

FOLLOW_UP_QUESTIONS:
1. [question]
2. [question]
3. [question]
"""

    prompt = f"""{cross_doc_prompt}

--- DOCUMENT CONTEXT ---
{context}
--- END CONTEXT ---

Question: {question}

Provide a thorough answer with document and page citations."""

    response = llm.invoke(prompt)
    full_answer = response.content

    # Parse follow-ups
    follow_ups = []
    answer_text = full_answer
    if "FOLLOW_UP_QUESTIONS:" in full_answer:
        parts = full_answer.split("FOLLOW_UP_QUESTIONS:")
        answer_text = parts[0].strip()
        for line in parts[1].strip().split("\n"):
            match = re.match(r'^\d+\.\s*(.+)', line.strip())
            if match:
                follow_ups.append(match.group(1).strip())

    return {
        "answer": answer_text,
        "pages_cited": sorted(pages_cited),
        "sections_cited": sorted(sections_cited),
        "chunks_used": len(all_results),
        "confidence": confidence,
        "follow_up_questions": follow_ups[:3],
        "documents_searched": docs_searched
    }