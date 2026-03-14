# Research-Tool-health

Web app prototype for an AI-assisted health sciences literature search engine.

## Overview
This project provides a Next.js frontend and a FastAPI backend to:
- Accept a health science topic
- Extract keywords
- Search PubMed and Scopus (others are pluggable adapters)
- Filter results to English and year >= 2000
- Download citations as CSV
- Summarize abstracts/full text (when available)
- Provide critical appraisal, research gaps, and evidence quality

## Repository layout
- `frontend/` — Next.js UI
- `backend/` — FastAPI API service

## Quick start (local)
### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY=your_key
export SCOPUS_API_KEY=your_scopus_key   # if available
export PUBMED_EMAIL=you@example.com     # required by NCBI Entrez
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:3000 and search.

## Environment variables
Backend:
- `OPENAI_API_KEY`
- `SCOPUS_API_KEY` (optional)
- `PUBMED_EMAIL`
- `PUBMED_API_KEY` (optional)

Frontend:
- `NEXT_PUBLIC_API_BASE` (default: http://localhost:8000)