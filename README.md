# Research Tool Health

AI-assisted health sciences literature search across PubMed and Scopus with automatic summaries and CSV export.

## Stack
- FastAPI backend (Python)
- Next.js frontend (React)
- Docker + Docker Compose

## Quick start

1. Copy environment templates

   - backend/.env.example -> backend/.env
   - frontend/.env.example -> frontend/.env

2. Fill in your API keys in backend/.env

3. Run the stack

   ```bash
   make up
   ```

4. Open the UI

   - Frontend: http://localhost:3000
   - Backend: http://localhost:8000

## API

- GET /api/health
- POST /api/search

Example request body:

```json
{
  "topic": "wearable devices for hypertension monitoring",
  "max_results": 10,
  "include_full_text": false
}
```

## Notes
- PubMed requires PUBMED_EMAIL.
- Scopus results require SCOPUS_API_KEY.
- OpenAI summaries require OPENAI_API_KEY.
