import discord
from discord.ext import commands

class Connection(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"Logged in as {self.bot.user} (ID: {self.bot.user.id})")

async def setup(bot):
    await bot.add_cog(Connection(bot))
