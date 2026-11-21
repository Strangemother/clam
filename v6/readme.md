# v6

## Ask the decision model through LM Studio

From the repository root, run [ask_lmstudio.py](./ask_lmstudio.py). It uses
Python 3's standard library and defaults to `http://192.168.50.60:1234`.

```bash
python3 v6/ask_lmstudio.py --list-models
python3 v6/ask_lmstudio.py YOUR_MODEL_ID
python3 v6/ask_lmstudio.py YOUR_MODEL_ID "Your question here"
```

Use the ID printed for your decision model. Without a question, the script
asks the refund question below. If authentication is enabled, set the
`LM_STUDIO_API_TOKEN` environment variable before running the script.

### Equivalent curl requests

Start the LM Studio server and load your decision model. List the model IDs
the server exposes:

```bash
curl --fail-with-body --silent --show-error \
  http://192.168.50.60:1234/v1/models
```

Replace `YOUR_MODEL_ID` with the matching `data[].id` from that response:

```bash
curl --fail-with-body --silent --show-error \
  http://192.168.50.60:1234/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "YOUR_MODEL_ID",
    "messages": [
      {"role": "system", "content": "Answer with only Yes or No."},
      {"role": "user", "content": "Customer message: I was charged twice this month. Please refund one of the charges.\n\nQuestion: Is the customer asking for a refund?"}
    ]
  }'
```

The answer is in `choices[0].message.content`. For this example, the expected
answer is `Yes`. If authentication is enabled, add an
`Authorization: Bearer <token>` header to both requests.

## Custom decision payload

The `state` and `questions` fields below are for a custom decision endpoint,
not LM Studio's standard chat completions endpoint. Use this example only if
your server implements that payload at `/`.

```bash
curl http://192.168.50.60:1234/ -H "Content-Type: application/json" -d '{
  "state": "I was charged twice this month, please refund one of them.",
  "questions": {
    "refund":  {"type": "noul", "instructions": "Is the customer asking for a refund?"},
    "team":    {"type": "choice", "instructions": "Which team should handle this?",
                "criteria": {"billing": "Charges, refunds, invoices", "technical": "App or site faults",
                             "fraud": "Suspected unauthorised use"}},
    "urgency": {"type": "score", "instructions": "How urgent is this?",
                "criteria": ["Can wait", "Today", "Blocking the customer now"]}
  }
}'
```
