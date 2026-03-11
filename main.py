import os
from typing import TypedDict, Dict, Any
from langgraph.graph import StateGraph, END
from config import get_snowflake_connection

# 1. Define the state schema
class AgentState(TypedDict):
    temp_forecast: float
    load_forecast: float
    max_capacity: float
    gsi: float
    search_context: str
    mitigation_protocol: dict

# 2. Define the Agent Nodes

def searcher_node(state: AgentState) -> Dict[str, Any]:
    """
    Searcher Agent Task: Identify real-time grid alerts and local news about infrastructure failures.
    Tool: Tavily Search API.
    """
    print("---[SEARCHER AGENT]--- Searching for Grid Alerts...")
    
    # In a full implementation, integrate Tavily:
    # from langchain_community.tools.tavily_search import TavilySearchResults
    # search = TavilySearchResults(max_results=2)
    # results = search.invoke("ERCOT Level 1 Emergency infrastructure failures")
    
    # Mocking search results for scaffolding
    mock_search_results = "Warning: High temperatures predicted in Texas. Grid operating near peak capacity."
    
    return {"search_context": mock_search_results}


def analyst_node(state: AgentState) -> Dict[str, Any]:
    """
    Analyst Agent Task: Calculate Grid Stress Index (GSI).
    Tool: Snowflake Python Connector.
    """
    print("---[ANALYST AGENT]--- Querying Snowflake and computing GSI...")
    
    # Query Snowflake using config.py
    conn = get_snowflake_connection()
    cursor = conn.cursor()
    
    temp = 80.0
    try:
        cursor.execute("SELECT MAX_TEMPERATURE_AIR_2M_F FROM GLOBAL_WEATHER__CLIMATE_DATA_BY_PELMOREX_WEATHER_SOURCE.PWS_BI_SAMPLE.POINT_FORECAST_DAY WHERE MAX_TEMPERATURE_AIR_2M_F IS NOT NULL LIMIT 1")
        res = cursor.fetchone()
        if res:
            temp = float(res[0])
    except Exception as e:
        print(f"Warning: Weather query failed: {e}")

    load_forecast = 15000.0
    try:
        cursor.execute("SELECT DALOAD FROM YES_ENERGY__SAMPLE_DATA.YES_ENERGY_SAMPLE.DART_LOADS_SAMPLE WHERE DALOAD IS NOT NULL LIMIT 1")
        res = cursor.fetchone()
        if res:
            load_forecast = float(res[0])
    except Exception as e:
        print(f"Warning: Load query failed: {e}")
        
    cursor.close()
    conn.close()
    
    # Max capacity varies by grid (ERCOT peak is ~80k-85k MW). We use 85000.0 as scaffold/mock max capacity.
    max_capacity = 85000.0
    
    print(f"    -> Temp Forecast: {temp}F")
    print(f"    -> Load Forecast: {load_forecast} MW")
    print(f"    -> Max Capacity: {max_capacity} MW")
    
    # Calculate GSI: (Load_Forecast / Max_Capacity) + (0.02 * (Temp - 85F))
    gsi = (load_forecast / max_capacity) + (0.02 * (temp - 85))
    
    print(f"    -> Computed GSI: {gsi:.2f}")
    
    return {
        "temp_forecast": temp,
        "load_forecast": load_forecast,
        "max_capacity": max_capacity,
        "gsi": gsi
    }


import json
import google.generativeai as genai

def strategist_node(state: AgentState) -> Dict[str, Any]:
    """
    Strategist Agent Task: Synthesize Searcher and Analyst data. Outputs Grid Mitigation Protocol if GSI > 0.85
    Tool: LLM (Llama 3 via Groq).
    """
    print("---[STRATEGIST AGENT]--- Formulating Mitigation Protocol...")
    
    gsi = float(state.get("gsi", 0.0))
    search_context = str(state.get("search_context", ""))
    
    protocol = {}
    
    if gsi > 0.85:
        print("    -> CRITICAL: GSI exceeds 0.85 threshold. Initiating Protocol via Gemini LLM.")
        
        try:
            # Fallback to the provided key if not in env
            api_key = os.getenv("GEMINI_API_KEY", "AIzaSyChJ9DjttX9NHv1OcV9k2DH4GIZ2sBgVWk")
            genai.configure(api_key=api_key)
            prompt = f"The Grid Stress Index (GSI) is {gsi:.4f}, strictly exceeding the critical 0.85 threshold. Context: '{search_context}'. Generate a short structured JSON 'Grid Mitigation Protocol' suggesting actions like Load Shedding, Battery Discharge, etc. Include 'status', 'actions' (list of strings), 'urgency', and 'reason'."
            
            model = genai.GenerativeModel('gemini-2.5-flash')
            response = model.generate_content(
                f"You are an expert Power Grid Strategist AI. Always output pure valid {""}JSON.\n\n{prompt}",
                generation_config={"response_mime_type": "application/json"}
            )
            
            content = response.text
            if content:
                protocol = json.loads(content)
            else:
                raise ValueError("Empty response from Gemini")
            protocol['search_context_used'] = search_context
            
        except Exception as e:
            print(f"Error calling Gemini API: {e}")
            protocol = {
                "status": "CRITICAL",
                "action": ["Load Shedding", "Activate Battery Discharge"],
                "urgency": "High",
                "reason": f"GSI level at {gsi:.4f} exceeds strict threshold 0.85. (Failsafe protocol generated due to LLM error)",
                "search_context_used": search_context
            }
    else:
        print("    -> SAFE: GSI is within safe limits. No immediate action required.")
        protocol = {
            "status": "SAFE",
            "action": ["Monitor"],
            "urgency": "Low",
            "reason": f"GSI is {gsi:.4f}.",
            "search_context_used": search_context
        }
        
    return {"mitigation_protocol": protocol}


# 3. Scaffold the LangGraph Workflow

# Initialize the StateGraph
workflow = StateGraph(AgentState)

# Add nodes to the graph
workflow.add_node("searcher", searcher_node)
workflow.add_node("analyst", analyst_node)
workflow.add_node("strategist", strategist_node)

# Define the flow (edges)
workflow.set_entry_point("searcher")
workflow.add_edge("searcher", "analyst")
workflow.add_edge("analyst", "strategist")
workflow.add_edge("strategist", END)

# Compile the workflow
app = workflow.compile()


if __name__ == "__main__":
    print("=== Starting Multi-Agent Grid Risk Mitigation Workflow ===\n")
    
    # Initialize state with default values
    initial_state = {
        "temp_forecast": 0.0,
        "load_forecast": 0.0,
        "max_capacity": 0.0,
        "gsi": 0.0,
        "search_context": "",
        "mitigation_protocol": {}
    }
    
    # Execute the graph
    final_state = app.invoke(initial_state)
    
    print("\n=== FINAL OUTPUT ===")
    import json
    print(json.dumps(final_state.get("mitigation_protocol"), indent=2))
