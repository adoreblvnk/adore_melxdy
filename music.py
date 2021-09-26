import asyncio
import os
import random
import string

import discord
import spotipy
# NOTE: import spotipy to use Spotify API. credentials located at developer.spotify.com/dashboard/. credentials are in the syntax: SPOTIPY_CLIENT_ID & SPOTIPY_CLIENT_SECRET.
import youtube_dl
from discord import message
from discord.ext import commands
from discord.ext.commands import command
from dotenv import load_dotenv
from googleapiclient.discovery import build
from spotipy.oauth2 import SpotifyOAuth

load_dotenv()

# import pymongo
# NOTE: import pymongo if using DB function commands. add "pymongo" & "dnspython" in requirements.txt file. DB helps to save music volume.

# TODO: add playlist support.

# youtube_dl format options:
# audioquality: 0 best 9 worst.
# format: bestaudio / best / worstaudio.
# NOTE: noplaylist: None
ytdl_format_options = {
    "audioquality": 5,
    "format": "bestaudio",
    "outtmpl": "{}",
    "restrictfilenames": True,
    "flatplaylist": True,
    "nocheckcertificate": True,
    "ignoreerrors": True,
    "logtostderr": False,
    "extractaudio": True,
    "audioformat": "opus",
    "quiet": True,
    "no_warnings": True,
    "default_search": "auto",
    "source_address": "0.0.0.0"  # bind to IPV4 as IPV6 is potentially buggy.
}

# download youtube_dl options.
ytdl_download_format_options = {
    "format": "bestaudio/best",
    "outtmpl": "downloads/%(title)s.mp3",
    "reactrictfilenames": True,
    "noplaylist": True,
    "nocheckcertificate": True,
    "ignoreerrors": False,
    "logtostderr": False,
    "quiet": True,
    "no_warnings": True,
    "default_search": "auto",
    "source_addreacs": "0.0.0.0",  # bind to IPV4 as IPV6 is potentially buggy.
    "output": r"youtube-dl",
    "postprocessors": [{
        "key": "FFmpegExtractAudio",
        "preferredcodec": "mp3",
        "preferredquality": "320",
    }]
}

stim = {
    "default_search": "auto",
    "ignoreerrors": True,
    "quiet": True,
    "no_warnings": True,
    "simulate": True,  # do not keep the video files
    "nooverwrites": True,
    "keepvideo": False,
    "noplaylist": True,
    "skip_download": False,
    "source_address": "0.0.0.0"  # bind to IPV4 as IPV6 is potentially buggy.
}

ffmpeg_options = {
    "options": "-vn",
    # "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"
}


class Downloader(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):  # default volume at 50%.
        super().__init__(source, volume)
        self.data = data
        self.title = data.get("title")
        self.url = data.get("url")
        self.thumbnail = data.get("thumbnail")
        self.duration = data.get("duration")
        self.views = data.get("views")
        self.playlist = {}  # NOTE: if the url is part of playlist?

    @classmethod
    async def video_url(cls, url, ytdl, *, loop=None, stream=False):
        """
        download song file & data.
        """
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        song_list = {"queue": []}
        if "entries" in data:
            if len(data["entries"]) > 1:  # EAFP?
                playlist_titles = [title["title"] for title in data["entries"]]
                song_list = {"queue": playlist_titles}
                song_list["queue"].pop(0)
            data = data["entries"][0]
        filename = data["url"] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data), song_list

    async def get_info(self, url):
        """
        gets info of next song by not downloading actual file but merely the data of song / query.
        """
        yt = youtube_dl.YoutubeDL(stim)
        down = yt.extract_info(url, download=False)
        data1 = {"queue": []}  # NOTE: rename data1.
        if "entries" in down:
            if len(down["entries"]) > 1:  # inefficient coding, use try except?
                playlist_titles = [title["title"] for title in down["entries"]]
                data1 = {"title": down["title"], "queue": playlist_titles}
            down = down["entries"][0]["title"]
        return down, data1


class MusicPlayer(commands.Cog, name="music"):
    def __init__(self, bot):
        self.bot = bot
        self.player = {"audio_files": []}
        # self.music = self.database.find_one("music")
        # self.database_setup()

        if self.spotify_setup():
            self.sp = spotipy.Spotify(
                auth_manager=spotipy.SpotifyClientCredentials())
        # NOTE: comment out if not using spotipy.

    def database_setup(self):
        URL = os.getenv("MONGO")
        if URL is None:
            return False

    def spotify_setup(self):
        URL = os.getenv("SPOTIPY_CLIENT_ID")
        if URL is None:
            return False
        else:
            return True

    async def getSpotifyData(self, song, msg):
        readedSong = ""
        if "playlist" in song:
            songCount = 0
            songIterationCount = 100
            songList = {"queue": []}
            while songIterationCount == 100:
                songIterationCount = 0
                results = self.sp.playlist_tracks(
                    song, limit=None, offset=songCount)
                for items in results["items"]:
                    songCount += 1
                    songIterationCount += 1
                    entry = items["track"]["name"]
                    for artist in items["track"]["artists"]:
                        entry += " " + artist["name"]
                    if songCount == 1:
                        readedSong = entry
                    else:
                        songList["queue"].append(entry)
            if self.player[msg.guild.id]["queue"] is None:
                self.player[msg.guild.id]["queue"] = []
            await self.play(msg=msg, song=readedSong)
            await self.playlist(songList, msg)
        if "track" in song:
            data = self.sp.track(song)
            readedSong = data["name"]
            for artist in data["artists"]:
                readedSong += " " + artist["name"]
            await self.play(msg=msg, song=readedSong)
    # NOTE: comment out if not using spotipy.

    @property
    def random_color(self):
        return discord.Color.from_rgb(random.randint(1, 255), random.randint(1, 255), random.randint(1, 255))

    async def yt_info(self, song):
        """
        get info from YouTube.
        """
        API_KEY = os.getenv("API_KEY")  # NOTE: use os.getenv.
        youtube = build("youtube", "v3", developerKey=API_KEY)
        song_data = youtube.search().list(part="snippet").execute()
        return song_data[0]

    @commands.Cog.listener("in_voice_state_update")
    async def music_voice(self, user, before, after):
        """
        clears server"s playlist after adore_melxdy leaves channel.
        """
        if after.channel is None and user.id == self.bot.user.id:
            try:
                self.player[user.guild.id]["queue"].clear()
            except KeyError:
                # NOTE: server ID is not in bot"s local self.player dictionary.
                # server ID lost or was not in data before disconnecting.
                print(f"failed to get guild ID {user.guild.id}.")

    async def filename_generator(self):
        """
        generates a unique file name for song file to be named as.
        """
        chars = list(string.ascii_letters + string.digits)
        name = ""
        for i in range(random.randint(9, 25)):
            name += random.choice(chars)
        if name not in self.player["audio_files"]:
            return name
        return await self.filename_generator()

    async def playlist(self, data, msg):
        """
        if YouTube link is a playlist. add song into server's playlist inside self.player dictionary.
        """
        for i in data["queue"]:
            print(i)
            self.player[msg.guild.id]["queue"].append(
                {"title": i, "author": msg})

    async def queue(self, msg, song):
        """
        adds query / song into server queue.
        """
        title_1 = await Downloader.get_info(self, url=song)
        title, data = title_1[0], title_1[1]
        # NOTE: needs fix here.
        if data["queue"]:
            await self.playlist(data, msg)
            # NOTE: embed for better output.
            return await msg.send(f"added playlist {data['title']} to queue.")
        self.player[msg.guild.id]["queue"].append(
            {"title": title, "author": msg})
        # TODO: remove title()?
        return await msg.send(f"**{title} added to queue.**")

    async def voice_check(self, msg):
        """
        makes sure adore_melxdy leaves VC if music is not played for longer than 2 minutes.
        """
        if msg.voice_client is not None:
            await asyncio.sleep(120)
            if msg.voice_client is not None and msg.voice_client.is_playing() is False and msg.voice_client.paused() is False:
                await msg.voice_client.disconnect()

    async def clear_data(self, msg):
        """
        clears local dictionary data.
            remove file name from dictionary.
            remove file & filename forom directory.
            remove filename from global audio file names.
        """
        name = self.player[msg.guild.id]["name"]
        os.remove(name)
        self.player["audio_files"].remove(name)

    async def loop_song(self, msg):
        """
        loops current playing song by replaying the same audio file via discord.PCMVolumeTransformer()
        """
        source = discord.PCMVolumeTransformer(
            discord.FFmpegPCMAudio(self.player[msg.guild.id]["name"]))
        loop = asyncio.get_event_loop()
        try:
            msg.voice_client.play(
                source, after=lambda a: loop.create_task(self.done(msg)))
            msg.voice_client.source.volume = self.player[msg.guild.id]["volume"]
            # if str(msg.guild.id) in self.music:
            #     msg.voice_client.source.volume = self.music["vol"] / 100
        except Exception as e:
            # has no attribute play.
            print(e)  # NOTE: output back the error for later debugging.

    async def done(self, msg, msg_id: int = None):
        """
        runs when song completes. deletes 'Now Playing' message via ID.
        """
        if msg_id:
            try:
                message = await msg.channel.fetch_message(msg_id)
                await message.delete()
            except Exception as Error:
                print("Failed to get the message")
        if self.player[msg.guild.id]["reset"] is True:
            self.player[msg.guild.id]["reset"] = False
            return await self.loop_song(msg)
        if msg.guild.id in self.player and self.player[msg.guild.id]["repeat"] is True:
            return await self.loop_song(msg)
        await self.clear_data(msg)
        if self.player[msg.guild.id]["queue"]:
            queue_data = self.player[msg.guild.id]["queue"].pop(0)
            return await self.start_song(msg=queue_data["author"], song=queue_data["title"])
        else:
            await self.voice_check(msg)

    async def start_song(self, msg, song):
        new_opts = ytdl_format_options.copy()
        audio_name = await self.filename_generator()
        self.player["audio_files"].append(audio_name)
        new_opts["outtmpl"] = new_opts["outtmpl"].format(audio_name)
        ytdl = youtube_dl.YoutubeDL(new_opts)
        download1 = await Downloader.video_url(song, ytdl=ytdl, loop=self.bot.loop)
        download = download1[0]
        data = download1[1]
        self.player[msg.guild.id]["name"] = audio_name
        emb = discord.Embed(colour=self.random_color, title="now playing",
                            description=download.title, url=download.url)
        emb.set_thumbnail(url=download.thumbnail)
        emb.set_footer(
            text=f"requested by {msg.author.display_name}.", icon_url=msg.author.avatar_url)
        loop = asyncio.get_event_loop()
        if data["queue"]:
            await self.playlist(data, msg)
        msgId = await msg.send(embed=emb)
        self.player[msg.guild.id]["player"] = download
        self.player[msg.guild.id]["author"] = msg
        msg.voice_client.play(
            download, after=lambda a: loop.create_task(self.done(msg, msgId.id)))
        # if str(msg.guild.id) in self.music: # NOTE adds user"s default volume if in database
        #     msg.voice_client.source.volume= self.music[str(msg.guild.id)]["vol"] / 100
        msg.voice_client.source.volume = self.player[msg.guild.id]["volume"]
        return msg.voice_client

    @command(aliases=["p"])
    async def play(self, msg, *, song):
        """
        plays song with url / title from YouTube.
        `eg:` -play Indian Music.
        `command:` play(song_name)
        """
        
        if "spotify.com" in self.player:
            return await self.getSpotifyData(song=song, msg=msg)
        # NOTE: comment out if not using spotipy.

        if msg.guild.id in self.player:
            if msg.voice_client.is_playing() is True:  # NOTE: SONG CURRENTLY PLAYING
                return await self.queue(msg, song)
            if self.player[msg.guild.id]["queue"]:
                return await self.queue(msg, song)
            if msg.voice_client.is_playing() is False and not self.player[msg.guild.id]["queue"]:
                return await self.start_song(msg, song)
        else:
            # NOTE: THE ONLY PLACE WHERE NEW `self.player[msg.guild.id]={}` IS CREATED
            self.player[msg.guild.id] = {
                "player": None,
                "queue": [],
                "author": msg,
                "name": None,
                "reset": False,
                "repeat": False,
                "volume": 0.5
            }
            return await self.start_song(msg, song)

    @play.before_invoke
    async def before_play(self, msg):
        """
        check voice_client
        - user voice = None: please join a voice channel
        - bot voice == None: joins the user's voice channel
        - user and bot voice NOT SAME:
            - music NOT Playing AND queue EMPTY: join user's voice channel
            - items in queue: please join the same voice channel as the bot to add song to queue
        """
        if msg.author.voice is None:
            # TODO: remove title().
            return await msg.send("**please join a voice channel to play music**".title())
        if msg.voice_client is None:
            return await msg.author.voice.channel.connect()
        if msg.voice_client.channel != msg.author.voice.channel:
            # NOTE: Check player and queue.
            if msg.voice_client.is_playing() is False and not self.player[msg.guild.id]["queue"]:
                # NOTE: move bot to user's voice channel if queue does not exist.
                return await msg.voice_client.move_to(msg.author.voice.channel)
            if self.player[msg.guild.id]["queue"]:
                # NOTE: user must join same voice channel if queue exist.
                return await msg.send("please join the same voice channel as melxdy to add song to queue.")

    # @commands.has_permissions(manage_channels=True) # enable to require permissions to use command.
    @command(aliases=["loop"])
    async def repeat(self, msg):
        """
        repeat the currently playing or turn off by using the command again.
        `eg:` -repeat
        `command:` repeat()
        """
        if msg.guild.id in self.player:
            if msg.voice_client.is_playing() is True:
                if self.player[msg.guild.id]["repeat"] is True:
                    self.player[msg.guild.id]["repeat"] = False
                    return await msg.message.add_reaction(emoji="✅")
                self.player[msg.guild.id]["repeat"] = True
                return await msg.message.add_reaction(emoji="✅")
            return await msg.send("no audio currently playing.")
        return await msg.send("melxdy is not in voice channel or playing music.")

    # @commands.has_permissions(manage_channels=True) # enable to require permissions to use command.
    @command(aliases=["restartloop"])
    async def reset(self, msg):
        """
        restart the currently playing song from the begining.
        `eg:` -reset
        `command:` reset()
        """
        if msg.voice_client is None:
            return await msg.send(f"**{msg.author.display_name}, there is no audio currently playing from melxdy.**")
        if msg.author.voice is None or msg.author.voice.channel != msg.voice_client.channel:
            return await msg.send(f"**{msg.author.display_name}, you must be in the same voice channel as melxdy.**")
        if self.player[msg.guild.id]["queue"] and msg.voice_client.is_playing() is False:
            # TODO: remove title()
            return await msg.send("**no audio currently playing or songs in queue.**".title(), delete_after=25)
        self.player[msg.guild.id]["reset"] = True
        msg.voice_client.stop()

    # @commands.has_permissions(manage_channels=True) # enable to require permissions to use command.
    @command(aliases=["s"])
    async def skip(self, msg):
        """
        skip the current playing song.
        `eg:` -skip
        `command:` skip()
        """
        if msg.voice_client is None:
            # TODO: remove title()
            return await msg.send("**no music currently playing**".title(), delete_after=60)
        if msg.author.voice is None or msg.author.voice.channel != msg.voice_client.channel:
            return await msg.send("please join the same voice channel as melxdy.")
        if not self.player[msg.guild.id]["queue"] and msg.voice_client.is_playing() is False:
            # TODO: remove title()
            return await msg.send("**no songs in queue to skip**".title(), delete_after=60)
        self.player[msg.guild.id]["repeat"] = False
        msg.voice_client.stop()
        return await msg.message.add_reaction(emoji="✅")

    # @commands.has_permissions(manage_channels=True) # enable to require permissions to use command.
    @command()
    async def stop(self, msg):
        """
        stop the current playing songs and clear the queue.
        `eg:` -stop
        `command:` stop()
        """
        if msg.voice_client is None:
            return await msg.send("melxdy is not connected to a voice channel.")
        if msg.author.voice is None:
            return await msg.send("you must be in the same voice channel as the bot.")
        if msg.author.voice is not None and msg.voice_client is not None:
            if msg.voice_client.is_playing() is True or self.player[msg.guild.id]['queue']:
                self.player[msg.guild.id]['queue'].clear()
                self.player[msg.guild.id]['repeat'] = False
                msg.voice_client.stop()
                return await msg.message.add_reaction(emoji='✅')
            return await msg.send(f"**{msg.author.display_name}, there is no audio currently playing or songs in queue.**")

    # @commands.has_permissions(manage_channels=True) # enable to require permissions to use command.
    @command(aliases=["dc", "disconnect"])
    async def leave(self, msg):
        """
        disconnect the bot from the voice channel.
        `eg:` -leave
        `command:` leave()
        """
        if msg.author.voice is not None and msg.voice_client is not None:
            if msg.voice_client.is_playing() is True or self.player[msg.guild.id]["queue"]:
                self.player[msg.guild.id]["queue"].clear()
                msg.voice_client.stop()
                return await msg.voice_client.disconnect(), await msg.message.add_reaction(emoji="✅")
            return await msg.voice_client.disconnect(), await msg.message.add_reaction(emoji="✅")
        if msg.author.voice is None:
            return await msg.send("you must be in the same voice channel as melxdy to disconnect it via commands.")

    # @commands.has_permissions(manage_channels=True) # enable to require permissions to use command.
    @command()
    async def pause(self, msg):
        """
        pause the currently playing audio.
        `eg:` -pause
        `command:` pause()
        """
        if msg.author.voice is not None and msg.voice_client is not None:
            if msg.voice_client.is_paused() is True:
                return await msg.send("song is already paused.")
            if msg.voice_client.is_paused() is False:
                msg.voice_client.pause()
                await msg.message.add_reaction(emoji="✅")

    # @commands.has_permissions(manage_channels=True) # enable to require permissions to use command.
    @command(aliases=["unpause"])
    async def resume(self, msg):
        """
        resume the currently paused audio.
        `eg:` -resume
        `command:` resume()
        """
        if msg.author.voice is not None and msg.voice_client is not None:
            if msg.voice_client.is_paused() is False:
                return await msg.send("song is already playing.")
            if msg.voice_client.is_paused() is True:
                msg.voice_client.resume()
                return await msg.message.add_reaction(emoji="✅")

    @command(name="queue", aliases=["q"])
    async def _queue(self, msg):
        """
        show the current songs in queue.
        `eg:` -queue
        `command:` queue()
        """
        if msg.voice_client is not None:
            if msg.guild.id in self.player:
                if self.player[msg.guild.id]["queue"]:
                    emb = discord.Embed(
                        colour=self.random_color, title="queue")
                    emb.set_footer(
                        text=f"command used by {msg.author.name}.", icon_url=msg.author.avatar_url)
                    for i in self.player[msg.guild.id]["queue"]:
                        emb.add_field(
                            name=f"**{i['author'].author.name}**", value=i["title"], inline=False)
                    return await msg.send(embed=emb, delete_after=120)
        return await msg.send("no songs in queue.")

    @command(name="song-info", aliases=["song?", "nowplaying", "np"])
    async def song_info(self, msg):
        """
        show information about the current playing song.
        `eg:` -song-info
        `command:` song-into()
        """
        if msg.voice_client is not None and msg.voice_client.is_playing() is True:
            emb = discord.Embed(colour=self.random_color, title='Currently Playing',
                                description=self.player[msg.guild.id]['player'].title)
            emb.set_footer(
                text=f"{self.player[msg.guild.id]['author'].author.name}", icon_url=msg.author.avatar_url)
            emb.set_thumbnail(
                url=self.player[msg.guild.id]['player'].thumbnail)
            return await msg.send(embed=emb, delete_after=120)
        return await msg.send(f"**no songs currently playing.**", delete_after=30)

    @command(aliases=["movebot", "mb"])
    async def join(self, msg, *, channel: discord.VoiceChannel = None):
        """
        make bot join a voice channel you are in if no channel is mentioned.
        `eg:` -join (If voice channel name is entered, it'll join that one)
        `command:` join(channel:optional)
        """
        if msg.voice_client is not None:
            return await msg.send(f"melxdy is already in a voice channel\nDid you mean to use {msg.prefix}moveTo")
        if msg.voice_client is None:
            if channel is None:
                return await msg.author.voice.channel.connect(), await msg.message.add_reaction(emoji="✅")
            return await channel.connect(), await msg.message.add_reaction(emoji="✅")
        else:
            if msg.voice_client.is_playing() is False and not self.player[msg.guild.id]["queue"]:
                return await msg.author.voice.channel.connect(), await msg.message.add_reaction(emoji="✅")

    @join.before_invoke
    async def before_join(self, msg):
        if msg.author.voice is None:
            return await msg.send("you are not in a voice channel.")

    @join.error
    async def join_error(self, msg, error):
        if isinstance(error, commands.BadArgument):
            return msg.send(error)
        if error.args[0] == 'Command raised an exception: Exception: playing':
            return await msg.send("**please join the same voice channel as the bot to add song to queue.**".title())

    # @commands.has_permissions(manage_channels=True) # enable to require permissions to use command.
    @command(aliases=["vol"])
    async def volume(self, msg, vol: int):
        """
        change the volume of the bot.
        `eg:` -vol 100 (200 is the max)
        `permission:` manage_channels
        `command:` volume(amount:integer)
        """
        if vol > 200:  # TODO: fix negative vol, EAFP.
            vol = 200
        vol = vol / 100
        if msg.author.voice is not None:
            if msg.voice_client is not None:
                if msg.voice_client.channel == msg.author.voice.channel and msg.voice_client.is_playing() is True:
                    msg.voice_client.source.volume = vol
                    self.player[msg.guild.id]["volume"] = vol
                    # if (msg.guild.id) in self.music:
                    #     self.music[str(msg.guild.id)]["vol"]=vol
                    return await msg.message.add_reaction(emoji="✅")
        return await msg.send("**please join the same voice channel as the bot to use the command.**".title(), delete_after=30)

    @commands.command(brief="download songs.", description="[prefix]download <video url or title> Downloads the song", aliases=["dl"])
    async def download(self, ctx, *, song):
        """
        downloads the audio from given URL source & sends the audio source back to user to download from URL, the file will be removed from storage once sent.
        `eg`: -download Indian Music.
        `command`: download(url:required)
        `NOTE`: file size can't exceed 8MB, otherwise it will fail to upload and cause error.
        """
        try:
            with youtube_dl.YoutubeDL(ytdl_download_format_options) as ydl:
                if "https://www.youtube.com/" in song:
                    download = ydl.extract_info(song, True)
                else:
                    infosearched = ydl.extract_info("ytsearch:" + song, False)
                    download = ydl.extract_info(
                        infosearched["entries"][0]["webpage_url"], True)
                filename = ydl.prepare_filename(download)
                embed = discord.Embed(title="your download is ready.",
                                      description="please wait a moment while the file is being uploaded . . .")
                await ctx.send(embed=embed, delete_after=30)
                await ctx.send(file=discord.File(filename))
                os.remove(filename)
        except (youtube_dl.utils.ExtractorError, youtube_dl.utils.DownloadError):
            embed = discord.Embed(
                title="song couldn't be downloaded.", description=("Song: " + song))
            await ctx.send(embed=embed)

    @volume.error
    async def volume_error(self, msg, error):
        if isinstance(error, commands.MissingPermissions):
            return await msg.send("manage channels or admin perms required to change volume.", delete_after=30)


def setup(bot):
    bot.add_cog(MusicPlayer(bot))
