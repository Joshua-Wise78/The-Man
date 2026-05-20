import os
import discord
import wavelink
import typing
from discord.ext import commands
from discord import app_commands


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        """
          Loads the cog giving the uri, password to the node to connect to wavelink  
        """
        uri = os.getenv("LAVALINK_URI", "")
        password = os.getenv("LAVALINK_PASSWORD", "")

        node = wavelink.Node(uri=uri, password=password)
        await wavelink.Pool.connect(nodes=[node], client=self.bot, cache_capacity=100)

        del uri
        del password

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload):
        """
           Listener for the node to see if it is connected and ready
        """
        print(f"Lavalink Node connected: {payload.node.identifier}")

    @commands.Cog.listener()
    async def on_wavelink_track_end(self, payload: wavelink.TrackEndEventPayload):
        """
           Listener for the end of the song (track) to then play the next song or
           return and stop playing music
        """
        vc: wavelink.Player = payload.player

        if not vc:
            return

        if not vc.queue.is_empty:
            next_track = vc.queue.get()
            await vc.play(next_track)
        else:
            pass

    @commands.Cog.listener()
    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload):
        """
           Listener that plays at the start of every new track  
        """

        vc: wavelink.Player = payload.player
        if not vc or not hasattr(vc, 'reply_channel'):
            return

        track = payload.track

        # Create the embed
        embed = discord.Embed(
            title="Now Playing",
            description=f"**[{track.title}]({track.uri})**\nBy {track.author}",
            color=discord.Color.blurple()
        )

        # Set the view and send the dashboard
        view = NowPlayingView(vc)
        await vc.reply_channel.send(embed=embed, view=view)
            

    @app_commands.command(name="play", description="Enter url to play music.")
    @app_commands.guild_only()
    async def play(self, interaction: discord.Interaction, search: str):
        """
           Play function for the bot loads in tracks (songs) to be played
           has some default catches to make sure that the program does not crash  
        """

        # Interaction check to avoid hinting warnings
        user = typing.cast(discord.Member, interaction.user)
        if not user.voice:
            return await interaction.response.send_message("You need to be in a voice channel to use this command.")

        await interaction.response.defer()

        vc: wavelink.Player
        if not interaction.guild.voice_client:
            vc = await interaction.user.voice.channel.connect(cls=wavelink.Player)
            vc.reply_channel = interaction.channel
        else:
            vc = interaction.guild.voice_client

        # Attempt to search the track and add to the playlist
        try:
            tracks: wavelink.Search = await wavelink.Playable.search(search)
        except wavelink.exceptions.LavalinkLoadException:
            return await interaction.followup.send("❌ Failed to load track. If this is a Spotify link, check your API keys!")
            
        if not tracks:
            return await interaction.followup.send(f"Sorry, could not find results for: `{search}`")

        # Typecheck for a track
        if isinstance(tracks, wavelink.Playlist):
            added = 0
            max_songs = 100  
            
            for track in tracks[:max_songs]:
                vc.queue.put(track)
                added += 1
                
            if len(tracks) > max_songs:
                await interaction.followup.send(f"📃 Playlist too large! Added the first **{added}** songs from **{tracks.name}**.")
            else:
                await interaction.followup.send(f"📃 Added the playlist **{tracks.name}** ({added} songs) to the queue!")

        else:
            track = tracks[0]
            vc.queue.put(track)
            await interaction.followup.send(f"🎵 Added **{track.title}** to the queue!")

        # If we are not already playing then get the que
        if not vc.playing:
            await vc.play(vc.queue.get())

    @app_commands.command(name="skip", description="Skips the currently playing song.")
    @app_commands.guild_only()
    async def skip(self, interaction: discord.Interaction):
        """
           Skip function to skip the current song (track) that is being played
        """

        # Check to see if the bot is in the voice chat or not
        vc: wavelink.Player = interaction.guild.voice_client
        if not vc or not vc.connected:
            return await interaction.response.send_message("I'm not currently in a voice channel!")

        # Check to see if the bot is playing a track or not
        if not vc.playing: 
            return await interaction.response.send_message("There is nothing playing right now to skip!")

        # Skip song forcfully :)
        await vc.skip(force=True)
        await interaction.response.send_message("⏭️ Skipped the current song! Moving to the next one in queue...")

    @app_commands.command(name="stop", description="Stop playing whatever music.")
    @app_commands.guild_only()
    async def stop(self, interaction: discord.Interaction):
        """
           Stops the discord bot and makes him leave the discord call
        """

        vc: wavelink.Player = interaction.guild.voice_client
        if vc:
            await vc.disconnect()
            await interaction.response.send_message("Disconnected from voice and cleared the queue.")

        else:
            await interaction.response.send_message("I'm not currently in a voice channel.")

class NowPlayingView(discord.ui.View):
    def __init__(self, vc: wavelink.Player):
        super().__init__(timeout=None)
        self.vc = vc

    @discord.ui.button(label="Pause / Resume", style=discord.ButtonStyle.primary, emoji='⏯️')
    async def pause_resume(self, interaction: discord.Interaction, button: discord.ui.Button):
        """
           Pause and resume switch button for the discord bot  
        """
        if not self.vc:
            return await interaction.response.send_message("No active player found.", ephemeral==True)

        # Toggle for the pause/resume
        await self.vc.pause(not self.vc.paused)
        state = "Paused" if self.vc.paused else "Resumed"

        await interaction.response.send_message(f"{state} the music", ephemeral==True)

    @discord.ui.button(label="Skip", style=discord.ButtonStyle.secondary, emoji="⏭️")
    async def skip(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.vc and self.vc.playing:
            await self.vc.skip(force=True)
            await interaction.response.send_message("Track skipped!", ephemeral=True)
        else:
            await interaction.response.send_message("Nothing is playing right now.", ephemeral=True)

    @discord.ui.button(label="Stop", style=discord.ButtonStyle.danger, emoji="⏹️")
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.vc:
            await self.vc.disconnect()
            await interaction.response.send_message("Disconnected from voice.", ephemeral=True)
            self.stop()


async def setup(bot):
    await bot.add_cog(Music(bot))
