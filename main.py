import os
import discord
import typing
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

class TheMan(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True

        super().__init__(
            command_prefix="!",
            intents=intents,
        )

    async def setup_hook(self):
        """
           The setup for the different extensions inside of the program
        """
        inital_extensions = [
            "cogs.connection",
            "cogs.commands",
            "cogs.music"
        ]

        # For loop to go thru the extensions and add them individually
        for ext in inital_extensions:
            try:
                await self.load_extension(ext)
                print(f"Loaded extension {ext}")

            except Exception as e:
                print(f"Failed to load extension {ext}: {e}")

if __name__ == "__main__":
    bot = TheMan()
    bot.run(TOKEN)
