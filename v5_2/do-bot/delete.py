"""
curl -X DELETE \
  -H "Content-Type: application/json"  \
  -H "Authorization: Bearer $DIGITALOCEAN_TOKEN" \
  "https://api.digitalocean.com/v2/gen-ai/agent/5581-a745-11ef-bf8f-4e013e2ddde4"
"""
import json
import os
import sys
import requests

from creds import KEY
from list import list_agents


def main():
    """Delete an agent by name or UUID."""
    if len(sys.argv) < 2:
        print("Usage: python delete.py <agent_name_or_uuid>")
        return 1
    
    identifier = sys.argv[1]
    agent_uuid = find_agent(identifier)
    
    if not agent_uuid:
        print(f"Error: Agent '{identifier}' not found")
        return 1
    
    print(f"Deleting agent: {agent_uuid}")
    result = delete_agent(agent_uuid)
    
    # Save response
    filename = f"deleted-{identifier}.json"
    filepath = os.path.join(os.path.dirname(__file__), filename)
    with open(filepath, 'w') as f:
        json.dump(result, f, indent=4)
    
    print(f"Response saved to {filename}")
    print(json.dumps(result, indent=2))
    return 0


def find_agent(identifier):
    """Find agent UUID by name or return UUID if already valid format."""
    agents_data = list_agents()
    
    for agent in agents_data.get('agents', []):
        if agent['uuid'] == identifier or agent['name'] == identifier:
            return agent['uuid']
    
    return None


def delete_agent(agent_uuid):
    """Delete a DigitalOcean GenAI agent."""
    url = f"https://api.digitalocean.com/v2/gen-ai/agents/{agent_uuid}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {KEY}"
    }
    
    response = requests.delete(url, headers=headers)
    
    if response.status_code == 204:
        return {"success": True, "message": "Agent deleted"}
    
    try:
        return response.json()
    except json.JSONDecodeError:
        return {"status_code": response.status_code, "text": response.text}


if __name__ == "__main__":
    exit(main())
