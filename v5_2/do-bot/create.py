"""
https://docs.digitalocean.com/reference/doctl/reference/genai/agent/create/


create agent:

    curl -X POST \
        -H "Content-Type: application/json"  \
        -H "Authorization: Bearer dop_v1_9eb6a58d28b" \
        "https://api.digitalocean.com/v2/gen-ai/agents" \
        -d '{
          "name": "bunny-agent",
          "model_uuid": "88515689-75c6-11ef-bf8f-4e013e2ddde4",
          "instruction": "A clever little bunny",
          "description": "clever-bunny-agent",
          "project_id": "371797ef-0d46-4f33-96e3-b94548399e07",
          "tags": [],
          "region": "tor1",
          "knowledge_base_uuid": []
        }'

Good Response:

    {
      "agent": {
        "uuid": "34b48ece-df8b-11f0-b074-4e013e2ddde4",
        "name": "api-create",
        "created_at": "2025-12-22T23:09:02Z",
        "updated_at": "2025-12-22T23:09:02Z",
        "instruction": "be a weather reporter",
        "description": "weather-agent",
        "model": {
          "uuid": "d754f2d7-d1f0-11ef-bf8f-4e013e2ddde4",
          "name": "Llama 3.3 Instruct (70B)",
          "inference_name": "llama3.3-70b-instruct"
        },
        "deployment": {
          "uuid": "34ba3726-df8b-11f0-b074-4e013e2ddde4",
          "status": "STATUS_WAITING_FOR_DEPLOYMENT",
          "visibility": "VISIBILITY_PRIVATE"
        },
        "api_keys": [
          {"api_key": "S1yNLQnDFj8cX4uGTych4euTvktksaKt"}
        ],
        "project_id": "371797ef-0d46-4f33-96e3-b94548399e07",
        "region": "tor1"
      }
    }
"""
import json
import requests
from datetime import datetime

from creds import KEY, DEFAULT_PROJECT_ID, DEFAULT_REGION


def main():
    """CLI entry point for creating DigitalOcean agents."""
    print("\n=== DigitalOcean Agent Creator ===\n")
    
    instruction = input("Agent instruction: ").strip()
    if not instruction:
        print("Error: Instruction is required")
        return 1
    
    name = input("Agent name (press Enter for auto-generated): ").strip() or None
    description = input("Description (optional): ").strip() or None
    
    print("\nCreating agent...")
    result = make_generic_agent(
        instruction=instruction,
        name=name,
        description=description
    )
    
    print("\n" + "=" * 80)
    print(json.dumps(result, indent=2))
    print("=" * 80)
    return 0


def create_agent(name, model_uuid, instruction, description=None,
                 project_id=None, tags=None, region="tor1",
                 knowledge_base_uuid=None):
    """Create a DigitalOcean GenAI agent."""
    url = "https://api.digitalocean.com/v2/gen-ai/agents"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {KEY}"
    }
    
    data = {
        "name": name,
        "model_uuid": model_uuid,
        "instruction": instruction,
        "region": region
    }
    
    if description:
        data["description"] = description
    if project_id:
        data["project_id"] = project_id
    if tags:
        data["tags"] = tags
    if knowledge_base_uuid:
        data["knowledge_base_uuid"] = knowledge_base_uuid
    
    response = requests.post(url, headers=headers, json=data)
    result = response.json()
    
    if response.status_code != 201:
        result['_status_code'] = response.status_code
        result['_request_data'] = data
    else:
        # Save successful agent creation to JSON file
        import os
        filename = f"{name}.json"
        filepath = os.path.join(os.path.dirname(__file__), filename)
        with open(filepath, 'w') as f:
            json.dump(result, f, indent=4)
        print(f"Agent saved to {filename}")
    
    return result


def select_model():
    """Display model list and prompt user to select one."""
    url = "https://api.digitalocean.com/v2/gen-ai/models"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {KEY}"
    }
    
    response = requests.get(url, headers=headers)
    models = response.json().get('models', [])
    
    print("\nAvailable Models:")
    print("-" * 80)
    for i, model in enumerate(models, 1):
        print(f"{i:2}. {model['name']:<40} {model['id']}")
    
    while True:
        try:
            choice = input("\nSelect model number: ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(models):
                return models[idx]['uuid']
            print("Invalid selection. Try again.")
        except (ValueError, KeyboardInterrupt):
            print("\nCancelled.")
            return None


def make_generic_agent(instruction, name=None, model_uuid=None,
                       description=None, **kwargs):
    """Create agent with simplified parameters and smart defaults."""
    if not model_uuid:
        model_uuid = select_model()
        if not model_uuid:
            return {"error": "No model selected"}
    
    if not name:
        name = f"agent-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    project_id = kwargs.get('project_id', DEFAULT_PROJECT_ID)
    region = kwargs.get('region', DEFAULT_REGION)
    
    # Don't send project_id if it's the placeholder/example value
    if project_id == '37455431-84bd-4fa2-94cf-e8486f8f8c5e':
        print("\nWarning: Using example project_id from docs.")
        print("You may need to update DEFAULT_PROJECT_ID with your actual project.")
        project_id = None
    
    return create_agent(
        name=name,
        model_uuid=model_uuid,
        instruction=instruction,
        description=description,
        project_id=project_id,
        region=region
    )


if __name__ == "__main__":
    exit(main())

