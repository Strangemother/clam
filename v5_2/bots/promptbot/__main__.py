try:
    import bot
except ImportError:
    from . import bot

if __name__ == "__main__":
    client = bot.PromptBot()
    client.start()
