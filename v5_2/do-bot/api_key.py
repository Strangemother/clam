"""
curl -X POST \
  -H "Content-Type: application/json"  \
  -H "Authorization: Bearer $DIGITALOCEAN_TOKEN" \
  "https://api.digitalocean.com/v2/gen-ai/agents/1b418231-b7d6-11ef-bf8f-4e013e2ddde4/api_keys" \
  -d '{
    "agent_uuid": "1b418231-b7d6-11ef-bf8f-4e013e2ddde4",
    "name": "test-key"
  }'

Response:

{
  "api_key_info": {
    "created_at": "2023-01-01T00:00:00Z",
    "created_by": "12345",
    "deleted_at": "2023-01-01T00:00:00Z",
    "name": "example name",
    "secret_key": "example string",
    "uuid": "123e4567-e89b-12d3-a456-426614174000"
  }
}

"""
import json
import requests

from creds import KEY


def main():
    """Create an API key for the bunny-agent."""
    result = create_agent_api_key(
        agent_uuid="06a6a18e-df8e-11f0-b074-4e013e2ddde4",
        name="bunny-demo-key"
    )
    print(json.dumps(result, indent=2))
    return 0


def create_agent_api_key(agent_uuid, name):
    """Create an API key for a DigitalOcean GenAI agent."""
    url = f"https://api.digitalocean.com/v2/gen-ai/agents/{agent_uuid}/api_keys"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {KEY}"
    }
    data = {
        "agent_uuid": agent_uuid,
        "name": name
    }
    
    response = requests.post(url, headers=headers, json=data)
    return response.json()


def create_using_agent(data, key_name=None):
    """Create an API key using agent creation response data."""
    agent_uuid = data.get('agent', {}).get('uuid')
    if not agent_uuid:
        return {"error": "No agent UUID found in data"}
    
    if not key_name:
        agent_name = data.get('agent', {}).get('name', 'agent')
        key_name = f"{agent_name}-key"
    
    return create_agent_api_key(agent_uuid, key_name)


if __name__ == "__main__":
    exit(main())
