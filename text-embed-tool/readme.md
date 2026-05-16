Single-class version.

Files:

- `embed_tool.py` - the only code file; contains class `Embed`
- `run.py` - minimal example of loading and calling `Embed`
- `requirements.txt` - minimal install list

Install:

```bash
cd /workspaces/clam/text-embed-tool
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Usage:

```python
from embed_tool import Embed

embed = Embed(
	db_path="embed_tool_assets/knowledge.db",
	model_path="/absolute/path/to/model.gguf",
	sqlite_ai_package="sqliteai.binaries.cpu",
	embed_context="embedding_type=FLOAT32,normalize_embedding=1,pooling_type=mean",
	retrieve_context="embedding_type=FLOAT32,normalize_embedding=1,pooling_type=mean",
)

entry_id = embed.embed("Cats like warm windows.")
match = embed.retrieve("Tell me about cats.")
print(entry_id)
print(match)
```

Run example:

```bash
cd /workspaces/clam/text-embed-tool
python run.py
```

Notes:

- There is no Flask code left.
- The constructor now requires the context strings for `llm_context_create_embedding(...)`.
- If your model needs a different `embedding_type`, set it in both context strings.

