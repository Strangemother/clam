from __future__ import annotations

import os

from embed_tool import Embed


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "embed_tool_assets", "run_example.db")
MIN_SCORE = 0.95
EMBED_PREFIX = "memory: "
RETRIEVE_PREFIX = "query: "

INITIAL_SENTENCES = [
    "The bakery opens early for the breakfast crowd.",
    "Morning rain cooled the sidewalks before sunrise.",
    "Fresh basil grows quickly in a sunny kitchen window.",
    "The train arrives every ten minutes during rush hour.",
    "A steel bottle keeps cold water chilled for hours.",
    "The library stays quiet in the afternoon for focused reading.",
    "Roasted carrots taste sweeter with olive oil and salt.",
    "Small lamps make the room feel warmer at night.",
    "Weekly backups help protect project files from accidents.",
    "A short walk after lunch helps clear the mind.",
]

ADDITIONAL_SENTENCES = [
    "Young puppies learn best with short, calm training sessions.",
    "Reward a puppy right after the correct behavior.",
    "Short leash walks help young dogs focus during practice.",
    "Consistent cues make puppy training easier to understand.",
]

SUCCESS_QUERY = "The library stays quiet in the afternoon for focused reading."
FAIL_QUERY = "Young puppies learn best with short, calm training sessions."


# if os.path.exists(DB_PATH):
#     os.remove(DB_PATH)

embed = Embed(
    db_path=DB_PATH,
    #model_path="C:/Users/jay/.lmstudio/models/jinaai/jina-embeddings-v5-text-small-retrieval/v5-small-retrieval-Q8_0.gguf",
    model_path="C:/Users/jay/.lmstudio/models/Abiray/zembed-1-Q4_K_M-GGUF/zembed-1-Q4_K_M.gguf",
    
    sqlite_ai_package="sqliteai.binaries.cpu",
    embed_context="embedding_type=FLOAT32,normalize_embedding=1,pooling_type=mean",
    retrieve_context="embedding_type=FLOAT32,normalize_embedding=1,pooling_type=mean",
    embed_prefix=EMBED_PREFIX,
    retrieve_prefix=RETRIEVE_PREFIX,
)

embedded_ids = []
for sentence in INITIAL_SENTENCES:
    embedded_ids.append(embed.embed(sentence))

print({"embed": {"count": len(embedded_ids), "last_id": embedded_ids[-1]}})

success = embed.retrieve(SUCCESS_QUERY, min_score=MIN_SCORE)
print({"retrieve_success": success})

no_result = embed.retrieve(FAIL_QUERY, min_score=MIN_SCORE)
print({"retrieve_fail": no_result})

additional_ids = []
for sentence in ADDITIONAL_SENTENCES:
    additional_ids.append(embed.embed(sentence))

print({"embed_more": {"count": len(additional_ids), "last_id": additional_ids[-1]}})

pass_after_more = embed.retrieve(FAIL_QUERY, min_score=MIN_SCORE)
print({"retrieve_pass_after_more": pass_after_more})