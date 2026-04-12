"""
AgentStack Real-World Test: LangGraph + Gemini
This script demonstrates a real-world AI agent workflow using LangGraph 
and Google's Gemini API, fully instrumented with the AgentStack SDK.
"""
import os
import sys
import time
import asyncio
from typing import TypedDict, Annotated, List, Optional
from operator import add

# ── API CONFIGURATION ──────────────────────────────────────────────────────────
# Using provided Gemini API Key
GOOGLE_API_KEY = "AIzaSyBN8SwvienD35OeAwm1LbjC6msWeNRLWj0"
os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY

# AgentStack Configuration
os.environ["AGENTSTACK_COLLECTOR_URL"] = "http://agentstack-collector:4318"
os.environ["AGENTSTACK_API_KEY"] = "ak_agentstack_demo_key_2026"
os.environ["AGENTSTACK_PROJECT_ID"] = "real-world-test"

# Ensure SDK is in path
sys.path.insert(0, "/app/packages/sdk-python/src")

try:
    import agentstack
    from agentstack import observe
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langgraph.graph import StateGraph, END
except ImportError as e:
    # Try local relative path as fallback
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'packages', 'sdk-python', 'src')))
    try:
        import agentstack
        from agentstack import observe
        from langchain_google_genai import ChatGoogleGenerativeAI
        from langgraph.graph import StateGraph, END
    except ImportError:
        print(f"Deployment Error: Missing dependencies. Error: {e}")
        sys.exit(1)

# ── INITIALIZE AGENTSTACK ──────────────────────────────────────────────────────
# auto_instrument=True automatically monkey-patches LangGraph nodes
agentstack.init(auto_instrument=True)

# ── DEFINITIONS ────────────────────────────────────────────────────────────────
class AgentState(TypedDict):
    query: str
    plan: Optional[str]
    report: Optional[str]
    error: Optional[str]

# Create the LLM instance
# Using a more compatible model string
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest", temperature=0)

# ── NODES ──────────────────────────────────────────────────────────────────────
def planner_node(state: AgentState):
    """Analyze the query and create a research plan."""
    print("[INFO] Node [Planner]: Analyzing query...")
    query = state["query"]
    
    # Actually call Gemini
    prompt = f"Create a 3-step research plan for the following query: {query}. Keep it brief."
    try:
        response = llm.invoke(prompt)
        return {"plan": response.content}
    except Exception as e:
        print(f"[ERROR] Planner LLM Error: {e}")
        raise

def researcher_node(state: AgentState):
    """Execute the plan and synthesize findings."""
    print("[INFO] Node [Researcher]: Executing plan...")
    plan = state["plan"]
    
    # Actually call Gemini
    prompt = f"Based on this research plan: {plan}\n\nWrite a 2-paragraph report. Use markdown."
    try:
        response = llm.invoke(prompt)
        return {"report": response.content}
    except Exception as e:
        print(f"[ERROR] Researcher LLM Error: {e}")
        raise

def validator_node(state: AgentState):
    """Simulates a quality check or a safety filter."""
    print("[INFO] Node [Validator]: Checking output quality...")
    report = state["report"] or ""
    
    # Intentionally trigger an error for specific queries to test AgentStack's error tracing
    if "fail" in state["query"].lower():
        print("[WARNING] Simulating intentional failure for testing...")
        raise ValueError("Simulated Validation Error: Output contains restricted content policy violation.")
    
    return state

# ── BUILD GRAPH ────────────────────────────────────────────────────────────────
def build_agent():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("planner", planner_node)
    workflow.add_node("researcher", researcher_node)
    workflow.add_node("validator", validator_node)
    
    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "researcher")
    workflow.add_edge("researcher", "validator")
    workflow.add_edge("validator", END)
    
    return workflow.compile()

# ── RUN ────────────────────────────────────────────────────────────────────────
def run_test(query: str):
    print(f"\n[RUN] Running Agent with query: '{query}'")
    agent = build_agent()
    
    try:
        result = agent.invoke({"query": query})
        print("[SUCCESS] Agent Execution Finished Successfully.")
        print("-" * 50)
        print(result.get("report", "No report generated."))
        print("-" * 50)
    except Exception as e:
        print(f"[ERROR] Agent Execution Failed: {e}")

if __name__ == "__main__":
    # Test 1: Successful Research
    run_test("Explain why ClickHouse is fast specifically for telemetry data.")
    
    time.sleep(1)
    
    # Test 2: Failure Simulation (to see how errors look in the dashboard)
    run_test("Simulate a failure or restricted content scenario.")

    # Ensure traces are sent to local backend
    print("\nFlushing Traces to AgentStack Dashboard...")
    try:
        from agentstack.exporter import get_processor
        processor = get_processor()
        if processor:
            processor.flush()
    except Exception:
        pass
    print("Done! Explore the generated traces in the Dashboard.")

