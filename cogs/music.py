import os
import discord
import wavelink
import typing
import math
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

    @app_commands.command(name="queue", description="Shows the interactive music queue.")
    @app_commands.guild_only()
    async def queue(self, interaction: discord.Interaction):
        """
           Queue command that allows us to view the list of music that is active
           in the order to be played
        """
        vc: wavelink.Player = interaction.guild.voice_client

        if not vc or not vc.connected:
            return await interaction.response.send_message("I am not currently in a voice channel.", ephemeral=True)

        if not vc.current and vc.queue.is_empty:
            return await interaction.response.send_message("The queue is completely empty.", ephemeral=True)

        if hasattr(vc, 'queue_message'):
            try:
                await vc.queue_message.delete()
            except discord.HTTPException:
                pass 

        # Convert the wavelink queue into a standard list
        queue_list = list(vc.queue)
        
        # Make the new view
        view = QueuePaginationView(vc, queue_list)
        embed = view.generate_embed()

        await interaction.response.send_message(embed=embed, view=view)        
        vc.queue_message = await interaction.original_response()

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
    async def stop_music(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.vc:
            await self.vc.disconnect()
            await interaction.response.send_message("Disconnected from voice.", ephemeral=True)
            self.stop()

import math # Make sure to add this to the top of music.py

class QueuePaginationView(discord.ui.View):
    def __init__(self, vc: wavelink.Player, queue_list: list):
        super().__init__(timeout=180) 
        self.vc = vc
        self.queue_list = queue_list
        self.page = 0
        self.per_page = 10
        self.max_pages = math.ceil(len(self.queue_list) / self.per_page)

        self.update_buttons()

    def update_buttons(self):
        self.previous_button.disabled = self.page == 0
        self.next_button.disabled = self.page >= self.max_pages - 1 or self.max_pages == 0

    def generate_embed(self):
        embed = discord.Embed(title="🎵 Current Queue", color=discord.Color.blurple())
        
        # Only show "Now Playing" on the first page
        if self.vc.current and self.page == 0:
            embed.add_field(name="Now Playing:", value=f"🎶 **{self.vc.current.title}**", inline=False)

        # Calculate which songs to show based on the page number
        start_idx = self.page * self.per_page
        end_idx = start_idx + self.per_page
        current_page_songs = self.queue_list[start_idx:end_idx]

        if current_page_songs:
            upcoming_songs = ""
            for i, track in enumerate(current_page_songs, start=start_idx + 1):
                upcoming_songs += f"**{i}.** {track.title}\n"
            
            embed.add_field(name="Up Next:", value=upcoming_songs, inline=False)
        else:
            embed.description = "There are no upcoming songs in the queue."

        # Add a footer to show page numbers
        total_pages = max(1, self.max_pages)
        embed.set_footer(text=f"Page {self.page + 1}/{total_pages} • Total Songs: {len(self.queue_list)}")
        
        return embed

    @discord.ui.button(label="◀ Previous", style=discord.ButtonStyle.primary)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page -= 1
        self.update_buttons()

        # Edit message
        await interaction.response.edit_message(embed=self.generate_embed(), view=self)

    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.page += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.generate_embed(), view=self)


async def setup(bot):
    await bot.add_cog(Music(bot))
