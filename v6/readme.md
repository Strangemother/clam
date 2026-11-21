# v6

## Ask the decision model through LM Studio

From the repository root, run [ask_lmstudio.py](./ask_lmstudio.py). It uses
Python 3's standard library and defaults to `http://192.168.50.60:1234`.

```bash
python3 v6/ask_lmstudio.py --list-models
python3 v6/ask_lmstudio.py YOUR_MODEL_ID
python3 v6/ask_lmstudio.py YOUR_MODEL_ID "Turn on the heater"
```

The script lists loaded decision model instance IDs from `/api/v1/models`
and asks questions through `/v1/systemone`. Without a question or context,
it routes "Turn on the light" to one of `lightbulb`, `heater`, or `door`.
Pass `--context "..."` to provide a different routing context. If no IDs are
listed, check that the decision model is loaded (not just downloaded) in the
Developer tab on the same LM Studio server. Use `--base-url` if that server
has a different address.

If authentication is enabled, set the `LM_STUDIO_API_TOKEN` environment
variable before running the script.

## Choose Chromite abilities

Run [ask_chromite.py](./ask_chromite.py) with an environment description,
a pet-owner message, or both:

```bash
python3 v6/ask_chromite.py --list-models
python3 v6/ask_chromite.py YOUR_MODEL_ID \
  --context "A quiet room with the pet resting nearby"
python3 v6/ask_chromite.py YOUR_MODEL_ID "The pet owner says hello"
python3 v6/ask_chromite.py YOUR_MODEL_ID \
  "The pet owner says hello" --context "A quiet room"
```

The script asks a yes/no probability question for each Chromite ability and
prints the selected abilities as a JSON list. Abilities with a probability
of at least `0.5` are selected. It uses the same server, authentication, and
model-list options as `ask_lmstudio.py`.

### The routing request sent to LM Studio

```bash
curl --fail-with-body http://192.168.50.60:1234/v1/systemone \
  -H "Content-Type: application/json" -d '{
  "model": "YOUR_MODEL_ID",
  "state": "Select from one of these internal routes: lightbulb, heater, door.",
  "questions": {
    "route": {
      "type": "choice",
      "instructions": "Turn on the light",
      "criteria": {
        "lightbulb": "Control the lights",
        "heater": "Control the heating",
        "door": "Control the door"
      }
    }
  }
}'
```

The response contains the selected route in `answers.route`. If
authentication is enabled, add an `Authorization: Bearer <token>` header.
