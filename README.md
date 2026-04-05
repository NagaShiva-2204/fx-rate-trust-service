# Real-Time Data Aggregation Service

## Initial thought process
The main risk is user trust: free users see stale or broken data, then churn before even considering paid. So I focused on reliability signals, graceful degradation, and simple aggregation of multiple public sources. The MVP should surface freshness clearly, keep the UI responsive during partial outages, and avoid complicated infrastructure so we can ship in 60 minutes.

## What this includes
- FastAPI backend with a single `/api/rates` endpoint that aggregates real public FX APIs.
- React frontend that shows rates and a data freshness label.
- Resilient fallback and a short in-memory cache.

## Run locally

### Backend (FastAPI)
```bash
cd /Users/nagashivahanumandla/Downloads/Real-Time\ Data\ Aggregation\ Service/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend (React + Vite)
```bash
cd /Users/nagashivahanumandla/Downloads/Real-Time\ Data\ Aggregation\ Service/frontend
npm install
npm run dev
```

Visit `http://localhost:5173`.

## API
`GET /api/rates?base=USD&symbols=EUR,GBP,INR,JPY,AUD,CAD`

Example response:
```json
{
  "base": "USD",
  "rates": {
    "EUR": 0.92,
    "GBP": 0.79
  },
  "as_of": "2026-04-05T10:00:00+00:00",
  "fetched_at": "2026-04-05T10:02:00+00:00",
  "freshness": "fresh",
  "staleness_seconds": 120.0,
  "sources": ["open.er-api.com", "exchangerate.host"],
  "warnings": [],
  "errors": []
}
```
