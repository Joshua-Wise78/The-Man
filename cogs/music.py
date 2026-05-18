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
    @app_commands.guild_only()
    async def play(self, interaction: discord.Interaction, search: str):
        if not interaction.user.voice:
            return await interaction.response.send_message("You need to be in a voice channel to use this command.")

        await interaction.response.defer()

        vc: wavelink.Player
        if not interaction.guild.voice_client:
            vc = await interaction.user.voice.channel.connect(cls=wavelink.Player)
        else:
            vc = interaction.guild.voice_client

        tracks: wavelink.Search = await wavelink.Playable.search(search)
        if not tracks:
            return await interaction.followup.send(f"Sorry, could not find results for: `{search}`")

        if isinstance(tracks, wavelink.Playlist):
            added: int = vc.queue.extend(tracks)
            await interaction.followup.send(f"📃 Added the playlist **{tracks.name}** ({added} songs) to the queue!")
        else:
            track = tracks[0]
            vc.queue.put(track)
            await interaction.followup.send(f"🎵 Added **{track.title}** to the queue!")

        if not vc.is_playing():
            await vc.play(vc.queue.get())

    @app_commands.command(name="skip", description="Skips the currently playing song.")
    @app_commands.guild_only()
    async def skip(self, interaction: discord.Interaction):
        vc: wavelink.Player = interaction.guild.voice_client

        if not vc or not vc.connected:
            return await interaction.response.send_message("I'm not currently in a voice channel!")

        if not vc.is_playing():
            return await interaction.response.send_message("There is nothing playing right now to skip!")

        await vc.skip(force=True)
        
        await interaction.response.send_message("⏭️ Skipped the current song! Moving to the next one in queue...")

    @app_commands.command(name="stop", description="Stop playing whatever music.")
    async def stop(self, interaction: discord.Interaction):
        """Stops the music and disconnects the bot."""
        vc: wavelink.Player = interaction.guild.voice_client
        if vc:
            await vc.disconnect()
            await interaction.response.send_message("Disconnected from voice and cleared the queue.")
        else:
            await interaction.response.send_message("I'm not currently in a voice channel.")

async def setup(bot):
    await bot.add_cog(Music(bot))
