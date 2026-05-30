import os
from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

load_dotenv()

embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

def query_documents(question, collection_name="cliniq_docs"):
    # Load existing vector store
    vectorstore = Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        persist_directory="./chroma_db"
    )

    # Find relevant chunks
    results = vectorstore.similarity_search_with_score(question, k=4)

    # Build context with page numbers
    context_parts = []
    pages_cited = set()
    for doc, score in results:
        page_num = doc.metadata.get("page_number", "?")
        pages_cited.add(page_num)
        context_parts.append(
            f"[Page {page_num}]: {doc.page_content}"
        )

    context = "\n\n".join(context_parts)

    # Ask Claude with context
    llm = ChatAnthropic(
        model="claude-sonnet-4-6",
        temperature=0
    )

    prompt = f"""You are ClinIQ, an expert assistant for clinical trial documents.
Answer the question using ONLY the provided context.
Always cite the page number(s) where you found the information.
If the context doesn't contain the answer, say so honestly.

Context:
{context}

Question: {question}

Answer (with page references):"""

    response = llm.invoke(prompt)
    return {
        "answer": response.content,
        "pages_cited": sorted(pages_cited),
        "chunks_used": len(results)
    }

if __name__ == "__main__":
    question = "What is the inclusion criteria?"
    result = query_documents(question)
    print(f"\nQuestion: {question}")
    print(f"\nAnswer: {result['answer']}")
    print(f"\nPages cited: {result['pages_cited']}")