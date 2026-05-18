import discord
import wavelink
from discord.ext import commands
from discord import app_commands

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        node = wavelink.Node(uri="http://lavalink:2333", password="youshallnotpass")
        await wavelink.Pool.connect(nodes=[node], client=self.bot, cache_capacity=100)

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload):
        print(f"Lavalink Node connected: {payload.node.identifier}")

    @app_commands.command(name="play", description="Enter url to play music.")
    async def play(self, ctx: commands.Context, *, search: str):
        if not ctx.author.voice:
            return await ctx.send("You need to be in a voice channel to use this command.")

        vc: wavelink.Player
        if not ctx.voice_client:
            vc = await ctx.author.voice.channel.connect(cls=wavelink.Player)
        else:
            vc = ctx.voice_client

        tracks: wavelink.Search = await wavelink.Playable.search(search)
        if not tracks:
            return await ctx.send(f"Sorry can not find results for: {search}")

        track = tracks[0]
        await vc.play(track)

        await ctx.send(f"Playing: **{track.title}**")

    @app_commands.command(name="stop", description="Stop playing whatever music.")
    async def stop(self, ctx: commands.Context):
        """Stops the music and disconnects the bot."""
        vc: wavelink.Player = ctx.voice_client
        if vc:
            await vc.disconnect()
            await ctx.send("Disconnected from voice and cleared the queue.")
        else:
            await ctx.send("I'm not currently in a voice channel.")

async def setup(bot):
    await bot.add_cog(Music(bot))
