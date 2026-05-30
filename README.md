# ClinIQ

   AI-powered Q&A for clinical trial documents. Upload a protocol,
   ask questions in plain English, get answers with page and section references.

   ## What It Does
   - Upload clinical trial protocols (PDF)
   - Ask questions in plain English
   - Get AI-powered answers with exact page citations and section references
   - Section-aware chunking for clinical document types

   ## Tech Stack
   - **Backend:** Python FastAPI + LangChain + ChromaDB
   - **AI:** Anthropic Claude (claude-sonnet-4-6)
   - **Embeddings:** HuggingFace all-MiniLM-L6-v2 (free, local)
   - **Frontend:** Next.js + Tailwind (coming soon)

   ## Status
   - [x] PDF upload and text extraction
   - [x] Section-aware chunking (detects 20+ clinical document sections)
   - [x] Vector embeddings with ChromaDB
   - [x] RAG-powered Q&A with page + section citations
   - [x] REST API with FastAPI
   - [ ] Frontend UI
   - [ ] User authentication
   - [ ] Multi-document support
   - [ ] Deployment

   ## Running Locally
```bash
   cd backend
   python -m venv venv
   source venv/bin/activate          # Mac/Linux
   # venv\Scripts\activate           # Windows
   pip install -r requirements.txt
   python main.py
   # Open http://localhost:8000/docs for API testing
```

   ## Sample Questions You Can Ask
   - "What is the primary endpoint of this study?"
   - "What are the inclusion criteria?"
   - "How is the study drug administered?"
   - "What adverse events are monitored?"
   - "What is the sample size and how was it determined?"

   ## Architecture
   Built by Gaurav Gupta | Pharma AI & Clinical Operations