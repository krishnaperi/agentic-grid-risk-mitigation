from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import snowflake.connector
import os
from dotenv import load_dotenv

load_dotenv() # Load your .env.local keys

app = FastAPI()

# 1. Define what the incoming request looks like
class GridRequest(BaseModel):
    region: str

# 2. Your Snowflake Connection Logic
def get_snowflake_data(region: str):
    ctx = snowflake.connector.connect(
        user=os.getenv('SNOWFLAKE_USER'),
        password=os.getenv('SNOWFLAKE_PASSWORD'),
        account=os.getenv('SNOWFLAKE_ACCOUNT'),
        warehouse=os.getenv('SNOWFLAKE_WAREHOUSE'),
        database=os.getenv('SNOWFLAKE_DATABASE'),
        schema=os.getenv('SNOWFLAKE_SCHEMA')
    )
    # Put your specific "Analyst" SQL query here
    query = "SELECT * FROM LOAD_DATA WHERE region = %s LIMIT 1"
    cur = ctx.cursor()
    try:
        cur.execute(query, (region,))
        return cur.fetchone()
    finally:
        ctx.close()

# 3. The POST Endpoint
@app.post("/analyze-grid")
async def analyze(request: GridRequest):
    try:
        data = get_snowflake_data(request.region)
        # Here you could also call your LLM/Strategist logic
        return {"status": "success", "data": data, "recommendation": "Maintain current load."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))