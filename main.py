import asyncio
import os

import discord
from discord import activity
import youtube_dl
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()


def bot_prefix(bot, msg):
    """callable prefix for adore_melxdy. this can be edited for custom prefixes."""
    prefixes = ["-"]  # current bot prefix: "-".
    return commands.when_mentioned_or(*prefixes)(bot, msg)


bot = commands.Bot(command_prefix=bot_prefix, description="adore_melxdy: a music bot")

exts = ["music"]  # add Cog extensions here.


@bot.event
async def on_ready():
    song_name = "Indian Music"  # status name. 
    activity_type = discord.ActivityType.listening  # status type.
    await bot.change_presence(activity=discord.Activity(type=activity_type, name=song_name))
    print(bot.user.name)

for extension in exts:
    bot.load_extension(extension)

bot.run(os.environ["DISCORD_TOKEN"]) # enable if in production.

# if __name__ == "__main__": 
#     bot.run(os.environ["DISCORD_TOKEN"])