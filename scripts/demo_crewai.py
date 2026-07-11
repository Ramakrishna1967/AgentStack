"""Demo script to verify CrewAI Auto-Instrumentation in AgentStack.

This script should generate traces WITHOUT using the @observe decorator.
"""
import os
import sys

# Ensure we use the correct collector URL
os.environ["AGENTSTACK_COLLECTOR_URL"] = "http://localhost:8000"
os.environ["AGENTSTACK_API_KEY"] = "ak_demo123" # Mock API key

# Ensure local sdk is found
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'agentstack', 'packages', 'sdk-python', 'src')))

try:
    from agentstack import init
    from agentstack.tracer import Tracer
    from crewai import Agent, Task, Crew, Process
except ImportError as e:
    print(f"Skipping test, required modules missing: {e}")
    sys.exit(0)

# Initialize AgentStack with auto-instrumentation ON
init(
    project_id="demo-crewai",
    api_key="ak_demo123", # Mock API Key
    auto_instrument=True
)

def run_crewai_demo():
    print("Starting CrewAI demo workflow...")

    # Define a simple explicit agent
    researcher = Agent(
        role='Senior Research Analyst',
        goal='Uncover groundbreaking technologies in AI',
        backstory='You work at a leading tech think tank and are known for identifying emerging trends.',
        verbose=True,
        allow_delegation=False
    )

    # Define a simple task for the agent
    task1 = Task(
        description='Research exactly two sentences explaining what "Agentic Workflow" means in 2026.',
        expected_output='A concise two-sentence explanation.',
        agent=researcher
    )

    # Setup the crew
    crew = Crew(
        agents=[researcher],
        tasks=[task1],
        verbose=True,
        process=Process.sequential
    )

    # Execute the workflow
    result = crew.kickoff()
    
    print("\n--- Final Result ---")
    print(result)

    # Flush trace data to AgentStack
    print("\nFlushing telemetry data to AgentStack...")
    if hasattr(Tracer, 'get_tracer_provider'):
        provider = Tracer.get_tracer_provider()
        if provider:
            provider.force_flush()
    print("Done! Check the dashboard to verify CrewAI spans.")

if __name__ == "__main__":
    run_crewai_demo()
