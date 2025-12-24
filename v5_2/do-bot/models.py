"""
https://docs.digitalocean.com/reference/doctl/reference/genai/agent/create/

get models:

    curl -X GET \
        -H "Content-Type: application/json"  \
        -H "Authorization: Bearer $DIGITALOCEAN_TOKEN" \
        "https://api.digitalocean.com/v2/gen-ai/models"

create agent:

    curl -X POST \
        -H "Content-Type: application/json"  \
        -H "Authorization: Bearer $DIGITALOCEAN_TOKEN" \
        "https://api.digitalocean.com/v2/gen-ai/agents" \
        -d '{
          "name": "api-create",
          "model_uuid": "95ea6652-75ee013e2ddde4",
          "instruction": "be a weather reporter",
          "description": "weather-agent",
          "project_id": "31-84bd-4fa2-94cf-",
          "tags": [
            "tag1"
          ],
          "region": "tor1",
          "knowledge_base_uuid": [
            "9758a232-b351-11ef-bf8f-4e013e2ddde4"
          ]
        }'
"""

from creds import KEY


def get_models():
    import requests
    
    url = "https://api.digitalocean.com/v2/gen-ai/models"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {KEY}"
    }
    
    response = requests.get(url, headers=headers)
    return response.json()


def print_models():
    data = get_models()
    models = data.get('models', [])
    
    print(f"\n{'Name':<40} {'UUID'}")
    print("-" * 80)
    
    for model in models:
        name = model.get('name', 'N/A')
        uuid = model.get('uuid', 'N/A')
        print(f"{name:<40} {uuid}")
    
    print(f"\nTotal: {len(models)} models")


def save_and_print_models():
    import json
    
    data = get_models()
    
    with open('models.json', 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Saved response to models.json")
    
    models = data.get('models', [])
    print(f"\n{'Name':<40} {'UUID'}")
    print("-" * 80)
    
    for model in models:
        name = model.get('name', 'N/A')
        uuid = model.get('uuid', 'N/A')
        print(f"{name:<40} {uuid}")
    
    print(f"\nTotal: {len(models)} models")


if __name__ == "__main__":
    save_and_print_models()


