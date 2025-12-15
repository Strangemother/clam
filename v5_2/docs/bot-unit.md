# A Bot

A single Bot is a client for the LLM connection. It performs the following:

1. Is a self hosted server
2. Connects to the LLM
3. Sends and receives messages through the API
4. Responds to Jobs

A bot is fundmentally a micro-site dedicated to one job (the prompt). We can run many bots and allow inter-communication. Some bots require other bots, such as the memory-bot's requirement for title bot.

To run a bot, run it as a module:

    run -m bots.titlebot
    run -m bots.memorybot

