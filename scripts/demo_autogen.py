"""Demo script to verify AutoGen Auto-Instrumentation in AgentStack.

This script should generate traces WITHOUT using the @observe decorator.
"""
import os
import sys

# Ensure we use the correct collector URL
os.environ["OXLY_COLLECTOR_URL"] = "http://localhost:8000"
os.environ["OXLY_API_KEY"] = "ak_demo123" # Mock API key

# Ensure local sdk is found
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'agentstack', 'packages', 'sdk-python', 'src')))

try:
    from oxly import init
    from oxly.tracer import Tracer
    from autogen import ConversableAgent, Agent
except ImportError as e:
    print(f"Skipping test, required modules missing: {e}")
    sys.exit(0)

# Initialize AgentStack with auto-instrumentation ON
init(
    project_id="demo-autogen",
    api_key="ak_demo123", # Mock API Key
    auto_instrument=True
)

def run_autogen_demo():
    print("Starting AutoGen demo workflow...")

    cathy = ConversableAgent(
        name="cathy",
        system_message="You are a comedian. Always reply with a joke.",
        llm_config={"config_list": [{"model": "fake_model", "api_key": "fake_key"}]},
        human_input_mode="NEVER",
        max_consecutive_auto_reply=1
    )

    joe = ConversableAgent(
        name="joe",
        system_message="You are a tough audience. Always criticize the joke.",
        llm_config={"config_list": [{"model": "fake_model", "api_key": "fake_key"}]},
        human_input_mode="NEVER",
        max_consecutive_auto_reply=1
    )

    # For testing without a real LLM, we can inject a mock reply hook
    def mock_reply(agent, messages, sender, config):
        if agent.name == "cathy":
            return True, "Why did the chicken cross the road? To get to the other side!"
        return True, "That was not funny at all."

    cathy.register_reply([Agent, None], mock_reply, position=0)
    joe.register_reply([Agent, None], mock_reply, position=0)

    # Execute the conversation
    result = joe.initiate_chat(cathy, message="Tell me a joke.", max_turns=1)
    
    print("\n--- Final Chat History ---")
    print(result.chat_history if hasattr(result, 'chat_history') else "No history object returned in this version.")

    # Flush trace data to AgentStack
    print("\nFlushing telemetry data to AgentStack...")
    processor = Tracer.get_processor()
    if processor:
        processor.flush()
    print("Done! Check the dashboard to verify AutoGen spans.")

if __name__ == "__main__":
    run_autogen_demo()
