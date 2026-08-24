"""Main controller for discord bots."""

import asyncio
import logging
import os
import sys

import discord
from discord.ext import commands
from dotenv import load_dotenv
from rich.logging import RichHandler

"""
Todo:
    1. Map out connection point for music
        - Navidrome CRUD
        - Play music?
    2. Map out connection for Route-88 commands
"""

logging.basicConfig(
    level="INFO",
    format="%(message)s", 
    datefmt="[%X]",
    handlers=[RichHandler()],
)
log = logging.getLogger("rich")

load_dotenv()
try:
    TOKEN = os.getenv("DISCORD_TOKEN", "")
except KeyError as e:
    print(f"Missing enviornment variables {e}")
except ValueError:
    print("Error: Guild_ID is not a valid number")
    sys.exit(1)


intents = discord.Intents.default()
intents.message_content = True
intents.members = True

initial_extensions = [
    "cogs.status"
    "cogs.route88"
]

class TheMan(commands.Bot):
    """The Man entry point."""

    def __init__(self) -> None:
        """Init TheMan."""
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self) -> None:
        """Iterate cogs and extensions for setup."""
        ...

    async def on_ready(self) -> None:
        """On ready command."""
        print(f"Logged in as {self.user} (ID: {self.user.id})")

async def main() -> None:
    """Intro Main method."""
    bot = TheMan()
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())




