import discord
import wavelink
from discord.ext import commands

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        node = wafelink.Node(uri="http://127.0.0.1:2333", password="youshallnotpass")
        await wavelink.Pool.connect(node=[node], client=self.bot, cache_capacity=100)

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload):
        print(f"Lavalink Node connected: {payload.node.identifier}")

    @commands.command(name="play", description="Enter url to play music.")
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

        await ctx.send(f"Playing **{track.title}**")

async def setup(bot):
    await bot.add_cog(Music(bot))
