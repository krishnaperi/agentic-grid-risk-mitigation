import os
from typing import TypedDict, Dict, Any
from langgraph.graph import StateGraph, END
from config import get_snowflake_connection, get_groq_client

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
    try:
        conn = get_snowflake_connection()
        cursor = conn.cursor()
        
        temp = 80.0
        try:
            # Note: Using the database and schema from environment via config.py
            cursor.execute("SELECT MAX_TEMPERATURE_AIR_2M_F FROM PWS_BI_SAMPLE.POINT_FORECAST_DAY WHERE MAX_TEMPERATURE_AIR_2M_F IS NOT NULL LIMIT 1")
            res = cursor.fetchone()
            if res:
                temp = float(res[0])
        except Exception as e:
            print(f"Warning: Weather query failed: {e}")

        load_forecast = 15000.0
        try:
            cursor.execute("SELECT DALOAD FROM YES_ENERGY_SAMPLE.DART_LOADS_SAMPLE WHERE DALOAD IS NOT NULL LIMIT 1")
            res = cursor.fetchone()
            if res:
                load_forecast = float(res[0])
        except Exception as e:
            print(f"Warning: Load query failed: {e}")
            
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error in Analyst Node (Snowflake): {e}")
        temp = 80.0
        load_forecast = 15000.0

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

def strategist_node(state: AgentState) -> Dict[str, Any]:
    """
    Strategist Agent Task: Synthesize Searcher and Analyst data. Outputs Grid Mitigation Protocol.
    Tool: LLM (Llama 3 via Groq).
    """
    print("---[STRATEGIST AGENT]--- Formulating Mitigation Protocol...")
    
    gsi = float(state.get("gsi", 0.0))
    search_context = str(state.get("search_context", ""))
    
    protocol = {}
    
    # We trigger the LLM to get a structured protocol regardless of GSI, 
    # but the content will reflect the risk level.
    print(f"    -> Initiating Protocol formulation via Groq (Llama 3). GSI: {gsi:.4f}")
    
    try:
        client = get_groq_client()
        prompt = f"The Grid Stress Index (GSI) is {gsi:.4f}. Context: '{search_context}'. Generate a short structured JSON 'Grid Mitigation Protocol'. Include 'status' (SAFE, WARNING, or CRITICAL), 'actions' (list of strings), 'urgency' (Low, Medium, High), and 'reason'."
        
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert Power Grid Strategist AI. Always output pure valid JSON."
                },
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            model="llama3-8b-8192",
            response_format={"type": "json_object"}
        )
        
        content = chat_completion.choices[0].message.content
        if content:
            protocol = json.loads(content)
        else:
            raise ValueError("Empty response from Groq")
        protocol['search_context_used'] = search_context
        
    except Exception as e:
        print(f"Error calling Groq API: {e}")
        # Failsafe logic based on GSI
        if gsi > 0.85:
            protocol = {
                "status": "CRITICAL",
                "actions": ["Load Shedding", "Activate Battery Discharge"],
                "urgency": "High",
                "reason": f"GSI level at {gsi:.4f} exceeds strict threshold 0.85. (Failsafe protocol)",
            }
        else:
            protocol = {
                "status": "SAFE",
                "actions": ["Monitor"],
                "urgency": "Low",
                "reason": f"GSI is {gsi:.4f}. (Failsafe protocol)",
            }
        protocol['search_context_used'] = search_context
        
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
