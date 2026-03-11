# Grid Risk Mitigation API

This repository contains the backend API for the Grid Risk Mitigation system, designed to assess power grid resilience and provide actionable mitigation strategies in real-time.

It integrates regional power grid data, weather forecasts, and market intelligence to calculate a Grid Stability Index (GSI) and generate risk mitigation protocols.

## Tech Stack
- **FastAPI**: API framework for handling client requests.
- **Langchain & LangGraph**: Orchestration of data retrieval and analysis workflows.
- **Snowflake**: Data warehouse for querying historical and forecast grid data.
- **Groq**: Fast inference engine for generating mitigation protocols.
- **Tavily**: Live web search integration for real-time market and weather context.

## Endpoints

### `GET /`
Returns the status of the API.

### `GET /health`
Returns `{"status": "online"}` for monitoring and uptime checks.

### `POST /analyze-grid`
Main endpoint for analyzing grid stability.

**Request Body:**
```json
{
  "region": "ERCOT North"
}
```

**Response:**
```json
{
  "status": "success",
  "region": "ERCOT North",
  "temp": 95.0,
  "load": 75000,
  "gsi": 0.85,
  "analysis": {
    "risk_level": "High",
    "recommendations": [
      "Initiate demand response programs for industrial partners.",
      "Monitor substation transformer temperatures."
    ]
  }
}
```

## Running Locally

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Configure environment variables in `.env`:
   - `SNOWFLAKE_ACCOUNT`, `SNOWFLAKE_USERNAME`, etc.
   - `GROQ_API_KEY`
   - `TAVILY_API_KEY`
3. Run the development server:
   ```bash
   uvicorn api:app --reload --port 8000
   ```

## Deployment
This service is configured with CORS enabled for frontend applications and is suitable for deployment on platforms like Railway, Render, or Vercel.
