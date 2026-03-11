import os
import traceback
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from main import app as agent_app

app = FastAPI()

# 1. ALLOW VERCEL TO TALK TO RAILWAY (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, replace with your Vercel URL
    allow_methods=["*"],
    allow_headers=["*"],
)

class GridRequest(BaseModel):
    region: str

@app.post("/analyze-grid")
async def analyze(request: GridRequest):
    try:
        print(f"--- ANALYZING REGION: {request.region} ---")
        
        # Initialize state with default values
        initial_state = {
            "temp_forecast": 0.0,
            "load_forecast": 0.0,
            "max_capacity": 0.0,
            "gsi": 0.0,
            "search_context": "",
            "mitigation_protocol": {}
        }
        
        # Execute the LangGraph workflow
        final_state = agent_app.invoke(initial_state)
        
        protocol = final_state.get("mitigation_protocol", {})
        
        return {
            "status": "success", 
            "region": request.region,
            "temp": final_state.get("temp_forecast"),
            "load": final_state.get("load_forecast"),
            "gsi": final_state.get("gsi"),
            "analysis": protocol
        }
    except Exception as e:
        # This prints the REAL error to your Railway logs so you can see it
        print("--- API ERROR ---")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "online"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)