# Mnemo

Mnemo is a personal knowledge chatbot built on Retrieval-Augmented Generation (RAG). It lets users upload their own notes, journals, lecture PDFs, or documents, and ask natural-language questions about that content. 

Unlike generic AI chatbots, Mnemo answers grounded in the user's own material first, with clear transparency about what came from their notes versus what came from general knowledge.

## Core Features
- **Recall Mode**: Answers strictly from your uploaded notes and cites the exact source.
- **Elaboration Mode**: Expands on concepts using general LLM knowledge when asked to explain further.
- **Privacy-First**: Focuses on grounding answers securely in user-uploaded documents.

## Project Structure
- `frontend/`: React frontend (Vite)
- `backend/`: FastAPI backend with ChromaDB for vector storage and Retrieval-Augmented Generation
