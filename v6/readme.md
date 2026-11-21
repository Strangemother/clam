# v6

## Ask the decision model through LM Studio

From the repository root, run [ask_lmstudio.py](./ask_lmstudio.py). It uses
Python 3's standard library and defaults to `http://192.168.50.60:1234`.

```bash
python3 v6/ask_lmstudio.py --list-models
python3 v6/ask_lmstudio.py YOUR_MODEL_ID
python3 v6/ask_lmstudio.py YOUR_MODEL_ID "Was I charged twice?" \
  --state "My statement shows two identical charges."
```

The script lists loaded decision model instance IDs from `/api/v1/models`
and asks questions through `/v1/systemone`. Without a question or context,
it runs the refund example. If no IDs are listed, check that the decision
model is loaded (not just downloaded) in the Developer tab on the same
LM Studio server. Use `--base-url` if that server has a different address.

If authentication is enabled, set the `LM_STUDIO_API_TOKEN` environment
variable before running the script. Use `--chat` for regular chat models.

### Ask multiple decision questions with curl

```bash
curl --fail-with-body http://192.168.50.60:1234/v1/systemone \
  -H "Content-Type: application/json" -d '{
  "model": "YOUR_MODEL_ID",
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

The response contains an `answers` object keyed by question ID. If
authentication is enabled, add an `Authorization: Bearer <token>` header.
