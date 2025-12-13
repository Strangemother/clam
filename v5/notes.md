# Clam Project — Architecture & Tooling Notes

## Selector Bot

- The **Selector Bot** is given:
  - A user prompt
  - A list of candidate tools / prompts (treated as selectable rules)
- It replies using a **primary tool** chosen from that list.
- A **secondary layer** then activates the selected prompt or bot associated with that rule.
- This allows intent routing before execution.

---

## Prompts & Model Association

- Each prompt can declare a **range of associated models**.
- Default model selection is `auto`, derived from the client’s generic configuration.
- A prompt may explicitly specify a model:
  - If available, it is loaded.
  - If unavailable, alternatives are tried in order.
- Models can be **highlighted** (e.g. with a star ⭐):
  - Highlighted models are considered important.
  - If a highlighted model does not exist locally, it should be loaded.
  - If it cannot be loaded, a default fallback model is selected.
- Users may explicitly select `auto`, which defers model choice to the automatic selection logic.

---

## Terminal Tool

- The **Terminal Tool** allows users to initiate a direct, live chat with a selected small model.
- When launched:
  - If no default model is set, the user is presented with a selectable list of models.
- The terminal operates as an interactive conversation surface.

### Terminal Commands

- Supports switch commands such as:
  - `help`
  - `change-model`
- Models can be swapped **while the conversation is live**.

### Instruction Editing (“Gaslighting”)

- The terminal allows editing or replacing the **initial instruction** mid-conversation.
- This affects all future responses in that session.
- Intended primarily for **debug-level experimentation**, to observe how personality or behaviour can be adapted as a conversation evolves.

---

## Conversation Persistence Utility

- A utility exists to save conversation data in:
  - **Raw state**
  - **Message state**
- This enables conversations to be resumed after being closed, without loss of context.

---

## Cross-Bot Communication

- Supports **bot-to-bot communication** via the framework.
- Bots can chat with each other directly.
- Enables multi-participant rooms:
  - Multiple bots
  - Multiple human users
- All participants interact within the same shared conversation space.

---

## Cross-API Model Referencing

- Models can be requested across **multiple registered endpoints** (e.g. LLaMA, Aloma, others).
- Each endpoint is defined by a URL.
- Clients must be registered per endpoint.
- When a model is requested:
  - The system checks whether it is already loaded.
  - If not, it queries all registered endpoints in turn.
- Maintains:
  - A **client list** (endpoints)
  - A **model reference list**
- Model resolution is endpoint-agnostic and handled automatically by the framework.
