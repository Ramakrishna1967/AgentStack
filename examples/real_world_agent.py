"""
Oxly Real-World Test: LangGraph + Gemini
This script demonstrates a real-world AI agent workflow using LangGraph 
and Google's Gemini API, fully instrumented with the Oxly SDK.
"""
import os
import sys
import time
import logging
from typing import TypedDict, Optional

#  API CONFIGURATION 
# Get API keys from environment variables (NEVER hardcode in production)
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY environment variable is required")
os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY

# Oxly Configuration
os.environ.setdefault("OXLY_COLLECTOR_URL", "http://localhost:8000")
os.environ.setdefault("OXLY_API_KEY", os.environ.get("OXLY_API_KEY", ""))
os.environ.setdefault("OXLY_PROJECT_ID", "real-world-test")

# Ensure SDK is in path (for development only)
sdk_path = os.environ.get("OXLY_SDK_PATH", "/app/packages/sdk-python/src")
sys.path.insert(0, sdk_path)

try:
    import oxly
    from oxly import observe
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langgraph.graph import StateGraph, END
except ImportError as e:
    # Try local relative path as fallback
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'packages', 'sdk-python', 'src')))
    try:
        import oxly
        from oxly import observe
        from langchain_google_genai import ChatGoogleGenerativeAI
        from langgraph.graph import StateGraph, END
    except ImportError:
        print(f"Deployment Error: Missing dependencies. Error: {e}")
        sys.exit(1)

#  INITIALIZE OXLY 
# auto_instrument=True automatically monkey-patches LangGraph nodes
oxly.init(auto_instrument=True)

#  DEFINITIONS 
class AgentState(TypedDict):
    query: str
    plan: Optional[str]
    report: Optional[str]
    error: Optional[str]

# Create the LLM instance
# Using a more compatible model string
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash-latest", temperature=0)

#  NODES 
# Configure logging
logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

def planner_node(state: AgentState):
    """Analyze the query and create a research plan."""
    logger.info("Node [Planner]: Analyzing query...")
    query = state["query"]
    
    # Actually call Gemini
    prompt = f"Create a 3-step research plan for the following query: {query}. Keep it brief."
    try:
        response = llm.invoke(prompt)
        return {"plan": response.content}
    except Exception as e:
        logger.error(f"Planner LLM Error: {e}")
        raise

def researcher_node(state: AgentState):
    """Execute the plan and synthesize findings."""
    logger.info("Node [Researcher]: Executing plan...")
    plan = state["plan"]
    
    # Actually call Gemini
    prompt = f"Based on this research plan: {plan}\n\nWrite a 2-paragraph report. Use markdown."
    try:
        response = llm.invoke(prompt)
        return {"report": response.content}
    except Exception as e:
        logger.error(f"Researcher LLM Error: {e}")
        raise

def validator_node(state: AgentState):
    """Simulates a quality check or a safety filter."""
    logger.info("Node [Validator]: Checking output quality...")
    report = state["report"] or ""
    
    # Intentionally trigger an error for specific queries to test Oxly's error tracing
    if "fail" in state["query"].lower():
        logger.warning("Simulating intentional failure for testing...")
        raise ValueError("Simulated Validation Error: Output contains restricted content policy violation.")
    
    return state

#  BUILD GRAPH 
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

#  RUN 
def run_test(query: str):
    logger.info(f"Running Agent with query: '{query}'")
    agent = build_agent()
    
    try:
        result = agent.invoke({"query": query})
        logger.info("Agent Execution Finished Successfully.")
        print("-" * 50)
        print(result.get("report", "No report generated."))
        print("-" * 50)
    except Exception as e:
        logger.error(f"Agent Execution Failed: {e}")

if __name__ == "__main__":
    # Test 1: Successful Research
    run_test("Explain why ClickHouse is fast specifically for telemetry data.")
    
    time.sleep(1)
    
    # Test 2: Failure Simulation (to see how errors look in the dashboard)
    run_test("Simulate a failure or restricted content scenario.")

    # Ensure traces are sent to backend
    logger.info("Flushing Traces to Oxly Dashboard...")
    try:
        from oxly.exporter import get_processor
        processor = get_processor()
        if processor:
            processor.flush()
    except Exception as e:
        logger.warning(f"Failed to flush traces: {e}")
    logger.info("Done! Explore the generated traces in the Dashboard.")

