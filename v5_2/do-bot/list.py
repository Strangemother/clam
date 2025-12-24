"""
curl -X GET \
  -H "Content-Type: application/json"  \
  -H "Authorization: Bearer $DIGITALOCEAN_TOKEN" \
  "https://api.digitalocean.com/v2/gen-ai/agents"
"""
import json
import os
import requests

from creds import KEY


def main():
    """List all agents and save to JSON."""
    result = list_agents()
    
    filename = "agents.json"
    filepath = os.path.join(os.path.dirname(__file__), filename)
    with open(filepath, 'w') as f:
        json.dump(result, f, indent=4)
    
    print(f"Saved agents list to {filename}")
    print_status()
    return 0


def list_agents():
    """List all DigitalOcean GenAI agents."""
    url = "https://api.digitalocean.com/v2/gen-ai/agents"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {KEY}"
    }
    
    response = requests.get(url, headers=headers)
    return response.json()


def print_status():
    """Print current status of all agents."""
    print("\n" + "=" * 80)
    print("Current agents:")
    agents = list_agents()
    for agent in agents.get('agents', []):
        status = agent.get('deployment', {}).get('status', 'UNKNOWN')
        print(f"  - {agent['name']} ({agent['uuid']}) - {status}")
    print("=" * 80)


if __name__ == "__main__":
    exit(main())
