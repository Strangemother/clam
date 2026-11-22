"""Helpers for loading decision-model YAML prompts."""

from pathlib import Path
from typing import Any

import yaml


def load_prompt(
    path: Path,
    allow_image_examples: bool = False,
) -> dict[str, Any]:
    with path.open(encoding="utf-8") as prompt_file:
        prompt = yaml.safe_load(prompt_file)

    if not isinstance(prompt, dict):
        raise ValueError("Prompt must be a YAML object.")
    if not isinstance(prompt.get("state"), str):
        raise ValueError("Prompt must define a string 'state'.")
    questions = prompt.get("questions")
    if not isinstance(questions, dict) or not questions:
        raise ValueError("Prompt must define one or more 'questions'.")
    examples = prompt.get("examples", [])
    valid_examples = isinstance(examples, list) and all(
        isinstance(example, str) and example.strip()
        or (
            allow_image_examples
            and isinstance(example, dict)
            and isinstance(example.get("image"), str)
            and example["image"].strip()
            and (
                "text" not in example
                or isinstance(example["text"], str)
            )
        )
        for example in examples
    )
    if not valid_examples:
        raise ValueError("'examples' must be a list of non-empty strings.")

    for question in questions.values():
        if not isinstance(question, dict):
            raise ValueError("Each question must be a YAML object.")
        if "instructions" not in question and "instruction" in question:
            question["instructions"] = question.pop("instruction")

    prompt["examples"] = examples
    return prompt
