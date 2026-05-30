from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_anthropic import ChatAnthropic
from langchain_community.embeddings import HuggingFaceEmbeddings
import chromadb

# Use free local embeddings (no API cost!)
embeddings = HuggingFaceEmbeddings(
    model_name="all-MiniLM-L6-v2"
)

def chunk_pages(pages, chunk_size=1000, overlap=200):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=overlap
    )
    chunks = []
    for page in pages:
        page_chunks = splitter.split_text(page["content"])
        for chunk in page_chunks:
            chunks.append({
                "content": chunk,
                "page_number": page["page_number"]
            })
    return chunks

def create_vectorstore(chunks, collection_name="cliniq_docs"):
    texts = [c["content"] for c in chunks]
    metadatas = [{"page_number": c["page_number"]} for c in chunks]

    vectorstore = Chroma.from_texts(
        texts=texts,
        metadatas=metadatas,
        embedding=embeddings,
        collection_name=collection_name,
        persist_directory="./chroma_db"
    )
    return vectorstore

if __name__ == "__main__":
    from pdf_loader import load_pdf

    pages = load_pdf("sample_docs/Prot_000.pdf")
    chunks = chunk_pages(pages)
    print(f"Created {len(chunks)} chunks from {len(pages)} pages")

    vectorstore = create_vectorstore(chunks)
    print("Vector store created and saved!")   