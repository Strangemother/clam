# auto-prompt

An auto prompt defines as thus:

Assistant: "What am I?"
User: "You are a heater. Check your tools"
# prompt is sent to modeller.md
Understood.

---

The prompt is ready to run given a primary prompt engineer auto prompt bot.


# dr bot

User: "Dr bot. Heater is not acting as intended"

1. read micro models
2. find header
3. check response
4. Rewrite prompt
5. Check again

---

# Persona Points

Dynamic, Static, and Cached persona knowledge points

Key:

- Dynamic: Every call yields a new (fresh) value, e.g. "age"
- static: Typically unchanging, such _version_
- Cached: Made and managed by the assistant, e.g. "Name"


Values:

- current datetime: dynamic. The datetime right now
- Age: dynamic. A age in time delta since init date
- name: cached: the name of the assistant
- Current thought..

extras:

- persona color
- voice format

---

Other _dynamic_ style keys exist, managing the background of the bot, such as:

+ Current executing tasks: CLAM is distributed, at points we can as the info-bot "what are you doing", for it to yield its concurrent tasks, e.g. "talking to you, and thinking about trees".


