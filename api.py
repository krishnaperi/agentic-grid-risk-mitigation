import os
import traceback
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
import snowflake.connector

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

def get_snowflake_connection():
    # Load and format the private key from Railway variables
    raw_key = os.getenv('SNOWFLAKE_PRIVATE_KEY')
    if not raw_key:
        raise Exception("SNOWFLAKE_PRIVATE_KEY variable is missing!")
    
    # Fix potential newline issues from environment variables
    formatted_key = raw_key.replace("\\n", "\n")
    
    p_key = serialization.load_pem_private_key(
        formatted_key.encode(),
        password=os.getenv('SNOWFLAKE_PRIVATE_KEY_PASSPHRASE').encode(),
        backend=default_backend()
    )
    
    pkb = p_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )

    return snowflake.connector.connect(
        account=os.getenv('SNOWFLAKE_ACCOUNT'),
        user=os.getenv('SNOWFLAKE_USER'),
        private_key=pkb,
        warehouse=os.getenv('SNOWFLAKE_WAREHOUSE'),
        database=os.getenv('SNOWFLAKE_DATABASE'),
        schema=os.getenv('SNOWFLAKE_SCHEMA')
    )

@app.post("/analyze-grid")
async def analyze(request: GridRequest):
    try:
        ctx = get_snowflake_connection()
        cur = ctx.cursor()
        
        # Using parameterized query to prevent SQL injection
        query = "SELECT * FROM LOAD_ACTUALS_AND_FORECASTS WHERE region = %s LIMIT 5"
        cur.execute(query, (request.region.upper(),))
        data = cur.fetchall()
        
        ctx.close()
        return {
            "status": "success", 
            "region": request.region,
            "data": data, 
            "recommendation": "Maintain current load. System stable."
        }
    except Exception as e:
        # This prints the REAL error to your Railway logs so you can see it
        print("--- DATABASE ERROR ---")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "online"}