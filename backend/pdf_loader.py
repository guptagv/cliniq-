from pypdf import PdfReader

def load_pdf(file_path):
    reader = PdfReader(file_path)
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text.strip():
            pages.append({
                "content": text,
                "page_number": i + 1
            })
    return pages

if __name__ == "__main__":
    pages = load_pdf("sample_docs/Prot_000.pdf")
    print(f"Loaded {len(pages)} pages")
    print(f"\nFirst page preview:\n{pages[0]['content'][:500]}")