from __future__ import annotations

import os

from embed_tool import Embed


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

embed = Embed(
    db_path=os.path.join(BASE_DIR, "embed_tool_assets", "knowledge.db"),
    model_path="C:/Users/jay/.lmstudio/models/jinaai/jina-embeddings-v5-text-small-retrieval/v5-small-retrieval-Q8_0.gguf",
    sqlite_ai_package="sqliteai.binaries.cpu",
    embed_context="embedding_type=FLOAT32,normalize_embedding=1,pooling_type=mean",
    retrieve_context="embedding_type=FLOAT32,normalize_embedding=1,pooling_type=mean",
)

entry_id = embed.embed("Cats like warm windows.")
print({"embed": entry_id})

match = embed.retrieve("Tell me about cats.")
print({"retrieve": match})