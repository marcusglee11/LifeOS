
import os
import sys
from runtime.agents.api import call_agent, AgentCall

def test_call_agent():
    print("Testing call_agent with reviewer_architect role...")
    
    call = AgentCall(
        role="reviewer_architect",
        packet={
            "subject_packet": {"goal": "Test goal", "payload": "Test payload"},
            "review_type": "build_review"
        },
        model="auto"
    )
    
    try:
        response = call_agent(call)
        print("SUCCESS!")
        print(f"Model used: {response.model_used}")
        print(f"Verdict: {response.packet.get('verdict') if response.packet else 'N/A'}")
        print(f"Rationale: {response.content[:100]}...")
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    test_call_agent()
