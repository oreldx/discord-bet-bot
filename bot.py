from utils.help import MyNewHelp

import os
import asyncio
import configparser
import random
import json

from dotenv import load_dotenv
import discord
from discord.ext import commands, tasks


intents = discord.Intents.all()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=commands.MinimalHelpCommand())

bot.help_command = MyNewHelp()

config = configparser.ConfigParser()
config.read('creds/creds.ini')
load_dotenv()
token = os.environ.get("DISCORD_TOKEN") 


@bot.event
async def load():
    for files in os.listdir('./cogs'):
        if files.endswith('.py'):
            await bot.load_extension(f'cogs.{files[:-3]}')


@bot.event
async def on_ready():
    print("Bot is online!")
    display_status.start()


@tasks.loop(seconds=60)
async def display_status():
    with open('status.json', 'r') as f:
        status = json.load(f)
    game = discord.Game(random.choice(status))
    await bot.change_presence(status=discord.Status.online, activity=game)


async def main():
    await load()
    await bot.start(token)

asyncio.run(main())
