import requests
import json
import time

url = 'http://192.168.50.60:42004/gradio_api/call/generate_unified_tts'
payload = {
    'data': [
        'hello from clam',
        'None',
        'None',
        1.0,
        0
    ]
}

print(f'Sending POST to {url}...')
try:
    response = requests.post(url, json=payload, timeout=20)
    print(f'POST Status Code: {response.status_code}')
    if response.status_code == 200:
        event_id = response.json().get('event_id')
        print(f'Event ID: {event_id}')
        if event_id:
            event_url = f'{url}/{event_id}'
            print(f'Getting event data from {event_url}...')
            with requests.get(event_url, stream=True, timeout=30) as r:
                lines = []
                for line in r.iter_lines():
                    if line:
                        decoded_line = line.decode('utf-8')
                        lines.append(decoded_line)
                        if len(lines) >= 20:
                            break
                print('--- START OF GET RESPONSE ---')
                for l in lines:
                    print(l)
                print('--- END OF GET RESPONSE ---')
                
                full_text = '\n'.join(lines)
                if 'FileData' in full_text:
                     print('Response type: FileData')
                elif 'http' in full_text:
                     print('Response type: direct URL')
                else:
                     print('Response type: unknown')
    else:
        print(f'POST failed: {response.status_code} {response.text}')
except Exception as e:
    print(f'Error: {e}')
