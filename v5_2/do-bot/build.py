"""
A script to easily create DigitalOcean GenAI agents via the API.

1. As for instructions file or string
2. As for model selection from available models
3. optional name, description, tags, etc.

The created agent details are saved to a JSON file. then

1. create a new API key for the new agent 
2. List the agents.
"""
import json
import os
import time
from datetime import datetime

from create import create_agent, select_model
from api_key import create_agent_api_key
from list import print_status
from creds import DEFAULT_PROJECT_ID, DEFAULT_REGION


def main():
    """Build and configure a new DigitalOcean GenAI agent."""
    print("\n=== DigitalOcean Agent Builder ===\n")
    
    # Get instruction
    instruction_file = input("Instruction file path (or press Enter to type): ").strip()
    if instruction_file and os.path.exists(instruction_file):
        with open(instruction_file, 'r') as f:
            instruction = f.read().strip()
        print(f"Loaded instruction from {instruction_file}")
    else:
        instruction = input("Agent instruction: ").strip()
    
    if not instruction:
        print("Error: Instruction is required")
        return 1
    
    # Get optional fields
    name = input("Agent name (press Enter for auto-generated): ").strip()
    if not name:
        name = f"agent-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    description = input("Description (optional): ").strip() or None
    
    # Select model
    model_uuid = select_model()
    if not model_uuid:
        print("Error: No model selected")
        return 1
    
    # Create agent
    print("\nCreating agent...")
    agent_result = create_agent(
        name=name,
        model_uuid=model_uuid,
        instruction=instruction,
        description=description,
        project_id=DEFAULT_PROJECT_ID,
        region=DEFAULT_REGION
    )
    
    status_code = agent_result.get('_status_code')
    if status_code and status_code not in (200, 201):
        print("Error creating agent:")
        print(json.dumps(agent_result, indent=2))
        return 1
    
    agent_uuid = agent_result.get('agent', {}).get('uuid')
    if not agent_uuid:
        print("Error: No agent UUID in response")
        print(json.dumps(agent_result, indent=2))
        return 1
    
    print(f"\nAgent created: {agent_uuid}")
    print(json.dumps(agent_result, indent=2))
    
    # Wait for deployment
    print("\nWaiting 5 seconds for agent deployment...")
    time.sleep(5)
    
    # Create API key
    print("\nCreating API key...")
    key_name = f"{name}-key"
    key_result = create_agent_api_key(agent_uuid, key_name)
    print(json.dumps(key_result, indent=2))
    
    # List all agents
    print_status()
    print(f"\nBuild complete! Agent '{name}' is ready.")
    return 0


if __name__ == "__main__":
    exit(main())