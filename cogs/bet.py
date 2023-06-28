from discord.ext import commands
from discord import Embed, ButtonStyle, ui
from dotenv import dotenv_values

import os
from hashlib import blake2s
from datetime import datetime
import locale

from utils import read_json_file, create_json_file


class Bet(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        env = dotenv_values()
        self.storage_path = env.get("STORAGE_PATH")
        self.check_storage()

        self.hash_function = blake2s(digest_size=10)


    @commands.command()
    async def create(self, ctx, *, message: str):
        stored_bets = read_json_file(self.storage_path)
        author = str(ctx.author.id)

        if author not in stored_bets:
            stored_bets[author] = self.initiate_object_author(ctx.author)
        if self.hash_function.hexdigest() not in stored_bets[author]['bets']:

            self.hash_function.update(message.encode('utf-8'))
            bet_hash = self.hash_function.hexdigest()
            current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            stored_bets[author]['bets'][bet_hash] = {
                'content': message,
                'timestamp': current_timestamp,
                'positive': [],
                'negative': [],
            }

            create_json_file(self.storage_path, stored_bets)

            await ctx.send(f'prédiction mémorisée, ID: {self.hash_function.hexdigest()}')

            embed = Embed(title=f':game_die: NOUVELLE PRÉDICTION :sparkles:', description= f':crystal_ball: {message}')
            await ctx.send(embed=embed)

        else:
            await ctx.send(f'prédiction déjà mémorisée')


    @commands.command()
    async def show(self, ctx):
        stored_bets = read_json_file(self.storage_path)
        for user, data in stored_bets.items():
            title = 'Prédiction'
            if len(data['bets'].keys()) > 1:
                title += 's'
            embed = Embed(title=title)
            embed.set_author(name=data['infos']['name'], icon_url=data['infos']['avatar'])

            for id_bet, bet in data['bets'].items():
                embed.add_field(name=f"prédiction ID {id_bet}", value=bet['content'], inline=False)

        await ctx.send(embed=embed)



    def check_storage(self):
        if not os.path.exists(self.storage_path):
            create_json_file(self.storage_path, {})

    def initiate_object_author(self, member):
        return {
            'bets': {},
            'infos': {
                'avatar': member.avatar.url,
                'name': member.name,
            },
        }


async def setup(bot):
    await bot.add_cog(Bet(bot))