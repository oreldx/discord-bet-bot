from discord.ext import commands
from discord import Embed, utils
from dotenv import dotenv_values

import os
import asyncio

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
        self.choices = {
            'binary': { 
                'negative': '🔴',
                'postive': '🔵',
            },
        }
        self.default_bet_type = 'binary'


    @commands.command()
    async def create(self, ctx, *, content: str):
        stored_bets = read_json_file(self.storage_path)
        author = str(ctx.author.id)

        if author not in stored_bets:
            stored_bets[author] = self.init_better(ctx.author)

        if self.hash_function.hexdigest() not in stored_bets[author]['bets']:

            content = content.strip()
            bet_type = content.split(' ')[0]
            if bet_type in self.choices:
                content = content[len(bet_type)-1:]
            else: 
                bet_type = self.default_bet_type

            self.hash_function.update(content.encode('utf-8'))
            bet_hash = self.hash_function.hexdigest()
            current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            stored_bets[author]['bets'][bet_hash] = self.init_bet(content, current_timestamp, bet_type)
            create_json_file(self.storage_path, stored_bets)

            await ctx.send(f'prédiction mémorisée, ID: {self.hash_function.hexdigest()}')

            embed = Embed(title=f':game_die: NOUVELLE PRÉDICTION :sparkles:', description= f':crystal_ball: -{content}')
            embed.set_footer(text=f"{bet_hash} créée par {author}")

            message = await ctx.send(embed=embed)

            for choice_emoji in self.choices[bet_type].values():
                await message.add_reaction(choice_emoji)

        else:
            await ctx.send(f'prédiction déjà mémorisée')

    @commands.command()
    async def delete(self, ctx, bet_hash):
        stored_bets = read_json_file(self.storage_path)
        author = str(ctx.author.id)
        if author in stored_bets and bet_hash in stored_bets[author]['bets']:
            stored_bets[author]['bets'].pop(bet_hash)
            create_json_file(self.storage_path, stored_bets)

            await ctx.send(f'prédiction {bet_hash} supprimée')
        else:
            await ctx.send(f"aucune prédiction correspondate à l'utilisateur prédiction ou ID de la prédiction incorrect")

    @commands.command()
    async def show(self, ctx):
        stored_bets = read_json_file(self.storage_path)

        for data in stored_bets.values():
            title = 'Prédiction'
            if len(data['bets'].keys()) > 1:
                title += 's'
            embed = Embed(title=title)
            embed.set_author(name=data['infos']['name'], icon_url=data['infos']['avatar'])

            for bet in data['bets'].values():
                timestamp = datetime.strptime(bet['timestamp'], '%Y-%m-%d %H:%M:%S')
                timestamp = timestamp.strftime("%Y-%m-%d")
                prediction = bet['content']
                embed.add_field(name=f'[{timestamp}] - {prediction}', value='', inline=False)

                emojis = self.choices[bet['bet_type']]

                for emoji in emojis:
                    if len(bet[emoji]) > 0:
                        users = [await self.bot.fetch_user(user) for user in bet[emoji]]
                        users = [user.name for user in users]
                        users = (', ').join(users)
                        name = f'|       {emojis[emoji]} {emoji}'
                        embed.add_field(name=name, value=users, inline=False)

        await ctx.send(embed=embed)

    @commands.command()
    async def list(self, ctx):
        stored_bets = read_json_file(self.storage_path)
        author = str(ctx.author.id)
        
        embed = Embed()
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url)
        if author in stored_bets and len(stored_bets[author]['bets']) > 0:

            for bet_hash, bet in stored_bets[author]['bets'].items():
                embed.add_field(name=bet_hash, value=bet['content'], inline=False)

            await ctx.send(embed=embed)
        else:
            embed.add_field(name="Pas de prédictions trouvées", value="", inline=False)
            await ctx.send(embed=embed)


    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return
        
        if reaction.message.author.bot:

            users = [user async for user in reaction.users()]
            intented_message = False
            for user_reacted in users:
                if user_reacted.bot:
                    intented_message = True
                    break

            if intented_message:
                stored_bets = read_json_file(self.storage_path)
                embed = reaction.message.embeds[0]
                reacting_user = str(user.id)
                author = embed.footer.text.split(' ')[-1]
                bet_hash = embed.footer.text.split(' ')[0]
                bet = stored_bets[author]['bets'][bet_hash]
                
                emoji = str(reaction.emoji)
                emojis = {value: key for key, value in self.choices[bet['bet_type']].items()}

                if emoji in emojis:
                    # ADD new choice
                    if reacting_user not in bet[emojis[emoji]]:
                        bet[emojis[emoji]].append(reacting_user)
                    emojis.pop(emoji)

                    # DEL old possible choice
                    for other_emoji in emojis.values():
                        if reacting_user in bet[other_emoji]:
                            bet[other_emoji].remove(reacting_user)
                            break

                    create_json_file(self.storage_path, stored_bets)


    def check_storage(self):
        if not os.path.exists(self.storage_path):
            create_json_file(self.storage_path, {})

    def init_better(self, member):
        return {
            'bets': {},
            'infos': {
                'avatar': member.avatar.url,
                'name': member.name,
            },
        }
    
    def init_bet(self, content: str, timestamp: str, bet_type: str = 'binary'):
        return {
                'content': content,
                'timestamp': timestamp,
                'status': True,
                'bet_type': bet_type,
                'choices': {choice: [] for choice in self.choices[bet_type].keys()}
            }

async def setup(bot):
    await bot.add_cog(Bet(bot))