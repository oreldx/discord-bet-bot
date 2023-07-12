from discord.ext import commands
from discord import Embed, utils
from dotenv import dotenv_values

import os
import asyncio
from hashlib import md5
from datetime import datetime
import locale
import random

from utils.utils import read_json_file, create_json_file


class Bet(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        env = dotenv_values()
        self.storage_path = env.get("STORAGE_PATH")
        self.check_storage()

        self.bet_channel = int(env.get('BET_CHANNEL_ID'))

        self.choices = {
            'binary': { 
                'postive': '🔵',
                'negative': '🔴',
            },
        }
        self.default_bet_type = 'binary'

    @commands.Cog.listener()
    async def on_ready(self):
        stored_bets = read_json_file(self.storage_path)
        ctx = self.bot.get_channel(int(self.bet_channel))

        pins = await ctx.pins()
        for message in pins:
            await message.unpin()

        for author_id, author in stored_bets.items():
            for bet_hash, bet in author['bets'].items():
                if bet['status']:
                    message = await ctx.send(embed=self.format_output_create(False, bet_hash, author_id, bet['content']))
                    for choice_emoji in self.choices[bet['bet_type']].values():
                        await message.add_reaction(choice_emoji)
                    
                    await message.pin()

    @commands.command()
    async def create(self, ctx, *, content: str):
        """Permet de créer une prédiction avec son contenu"""
        self.check_correct_channel(ctx)

        stored_bets = read_json_file(self.storage_path)
        author = str(ctx.author.id)

        if author not in stored_bets:
            stored_bets[author] = self.init_author(ctx.author)

        content = content.strip()
        bet_type = content.split(' ')[0]
        if bet_type in self.choices:
            content = content[len(bet_type)-1:]
        else: 
            bet_type = self.default_bet_type
        
        bet_hash = md5(content.encode('utf-8')).hexdigest()
        existing_bet = bet_hash in stored_bets[author]['bets']

        if existing_bet:
            await ctx.send(self.format_output_create(existing_bet))
        else:
            current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            stored_bets[author]['bets'][bet_hash] = self.init_bet(content, current_timestamp, bet_type)
            create_json_file(self.storage_path, stored_bets)

            message = await ctx.send(embed=self.format_output_create(existing_bet, bet_hash, author, content))

            for choice_emoji in self.choices[bet_type].values():
                await message.add_reaction(choice_emoji)
            
            await message.pin()

    @commands.command()
    async def delete(self, ctx, bet_hash):
        """Permet de supprimer une prédiction avec ID"""
        self.check_correct_channel(ctx)

        stored_bets = read_json_file(self.storage_path)
        author = str(ctx.author.id)

        possible_deletion = author in stored_bets and bet_hash in stored_bets[author]['bets']

        if possible_deletion:
            stored_bets[author]['bets'].pop(bet_hash)
            create_json_file(self.storage_path, stored_bets)

            pins = await ctx.pins()
            for message in pins:
                if len(message.embeds) > 0:
                    embed = message.embeds[0]
                    author_embed = embed.footer.text.split(' ')[-1]
                    bet_hash_embed = embed.footer.text.split(' ')[0]
                    if bet_hash == bet_hash_embed and author == author_embed:
                        await message.unpin()

        await ctx.send(self.format_output_delete(possible_deletion, bet_hash))
        
    @commands.command()
    async def close(self, ctx, bet_hash):
        """Permet de terminer une prédiction grâce à son ID et d'afficher le résultat"""
        self.check_correct_channel(ctx)

        stored_bets = read_json_file(self.storage_path)
        author = str(ctx.author.id)

        
        possible_closing = author in stored_bets and bet_hash in stored_bets[author]['bets']
        
        data = []
        if possible_closing:
            stored_bets[author]['bets'][bet_hash]['status'] = False
            create_json_file(self.storage_path, stored_bets)

            author = stored_bets[author] 
            bet = author['bets'][bet_hash]
            timestamp = datetime.strptime(bet['timestamp'], '%Y-%m-%d %H:%M:%S')
            
            emojis = self.choices[bet['bet_type']]
            choices = []
            for emoji in emojis:
                if len(bet['choices'][emoji]) > 0:
                    choice_data = {}
                    users = [await self.bot.fetch_user(user) for user in bet['choices'][emoji]]
                    choice_data['users'] = [user.name for user in users]
                    choice_data['choice_emoji'] = emojis[emoji]
                    choice_data['choice_value'] = emoji
                    choices.append(choice_data)

            data.append({
                'name': author['infos']['name'],
                'avatar': author['infos']['avatar'],
                'bets': [{
                    'timestamp': timestamp.strftime("%Y-%m-%d"),
                    'content': bet['content'],
                    'choices': choices,
                }]
            })
            
            await ctx.send(embed=self.format_output_show(data)[0]) 

            pins = await ctx.pins()
            for message in pins:
                if len(message.embeds) > 0:
                    embed = message.embeds[0]
                    author_embed = embed.footer.text.split(' ')[-1]
                    bet_hash_embed = embed.footer.text.split(' ')[0]
                    if bet_hash == bet_hash_embed and author == author_embed:
                        await message.unpin()
        else:

            await ctx.send(self.format_output_close(possible_closing, bet_hash))


    @commands.command()
    async def open(self, ctx, bet_hash):
        """Permet de re-démarrer une prédiction grâce à son ID et de donner l'accès au vote"""
        self.check_correct_channel(ctx)

        stored_bets = read_json_file(self.storage_path)
        author = str(ctx.author.id)

        possible_opening = author in stored_bets and bet_hash in stored_bets[author]['bets']

        if possible_opening:
            stored_bets[author]['bets'][bet_hash]['status'] = True
            create_json_file(self.storage_path, stored_bets)

            bet = stored_bets[author]['bets'][bet_hash]
            message = await ctx.send(embed=self.format_output_create(False, bet_hash, author, bet['content']))
            for choice_emoji in self.choices[bet['bet_type']].values():
                await message.add_reaction(choice_emoji)
            
            await message.pin()
            
        else:
            await ctx.send(self.format_output_open(possible_opening, bet_hash))
        
    @commands.command()
    async def show(self, ctx):
        """Permet d'afficher les résultats de toutes LES prédictions en cours et terminées"""
        self.check_correct_channel(ctx)

        stored_bets = read_json_file(self.storage_path)

        data = []
        for author in stored_bets.values():
            author_data = {}
            
            author_data['name'] = author['infos']['name']
            author_data['avatar'] = author['infos']['avatar']
            author_data['bets'] = []
            for bet in author['bets'].values():
                bet_data = {}

                timestamp = datetime.strptime(bet['timestamp'], '%Y-%m-%d %H:%M:%S')
                bet_data['timestamp'] = timestamp.strftime("%Y-%m-%d")
                bet_data['content'] = bet['content']
                bet_data['choices'] = []

                emojis = self.choices[bet['bet_type']]
                for emoji in emojis:
                    if len(bet['choices'][emoji]) > 0:
                        choice_data = {}
                        users = [await self.bot.fetch_user(user) for user in bet['choices'][emoji]]
                        choice_data['users'] = [user.name for user in users]
                        choice_data['choice_emoji'] = emojis[emoji]
                        choice_data['choice_value'] = emoji

                        bet_data['choices'].append(choice_data)

                author_data['bets'].append(bet_data)

            data.append(author_data)

        for embed in self.format_output_show(data):
            await ctx.send(embed=embed) 

    @commands.command()
    async def list(self, ctx):
        """Permet de lister toutes TES prédictions avec leur ID et statut"""
        self.check_correct_channel(ctx)

        stored_bets = read_json_file(self.storage_path)
        author = str(ctx.author.id)
        author_name = ctx.author.name
        author_picture = ctx.author.avatar.url

        bets = {}
        if author in stored_bets and len(stored_bets[author]['bets']) > 0:
            bets = {bet_hash: bet['content'] for bet_hash, bet in stored_bets[author]['bets'].items()}

        await ctx.send(embed=self.format_output_list(author_name, author_picture, bets))

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
                
                if bet['status']:
                    emoji = str(reaction.emoji)
                    emojis = {value: key for key, value in self.choices[bet['bet_type']].items()}

                    if emoji in emojis:
                        # ADD new choice
                        if reacting_user not in bet['choices'][emojis[emoji]]:
                            bet['choices'][emojis[emoji]].append(reacting_user)
                        emojis.pop(emoji)

                        # DEL old possible choice
                        for other_emoji in emojis.values():
                            if reacting_user in bet['choices'][other_emoji]:
                                bet['choices'][other_emoji].remove(reacting_user)
                                break

                        create_json_file(self.storage_path, stored_bets)

    def check_correct_channel(self, ctx):
        if ctx.channel.id != self.bet_channel:
            raise commands.CheckFailure("Channel isn't valid!")

    def check_storage(self):
        if not os.path.exists(self.storage_path):
            create_json_file(self.storage_path, {})

    def init_author(self, member):
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
    
    


    def format_output_create(self, exisiting_bet: bool, bet_hash: str = '', author: str = '', content: str = ''):
        if exisiting_bet:
            return 'prédiction déjà mémorisée'
        else:
            embed = Embed(title=f':game_die: NOUVELLE PRÉDICTION :sparkles:', description= f':crystal_ball: -{content}')
            embed.set_footer(text=f"{bet_hash} créée par {author}")
            return embed

    def format_output_show(self, data: list):
        embeds = []
        
        for author in data:
            title = 'Prédiction'
            if len(author['bets']) > 1:
                title += 's'

            
            high = random.randint(200, 255)
            mid = random.randint(100, 199)
            low = random.randint(0, 99)
            r, g, b = random.sample([high, mid, low], 3)
            hex_color = int("{:02x}{:02x}{:02x}".format(r, g, b), 16)

            embed = Embed(title=title, color=hex_color)

            embed.set_author(name=author['name'], icon_url=author['avatar'])

            for bet in author['bets']:
                timestamp = bet['timestamp']
                prediction = bet['content']
                embed.add_field(name=f'[{timestamp}] - {prediction}', value='', inline=False)

                for choice in bet['choices']:
                    users = ('\n').join(choice['users'])
                    value =f"```\n{users}\n```"
                    name = f' {choice["choice_emoji"]} {choice["choice_value"]}'
                    embed.add_field(name=name, value=value, inline=True)

            embeds.append(embed)

        return embeds

    def format_output_list(self, author_name: str, author_picture: str, bets: dict,):
        embed = Embed()
        embed.set_author(name=author_name, icon_url=author_picture)

        for bet_hash, bet in bets.items():
            embed.add_field(name=bet_hash, value=bet, inline=False)
        
        if len(bets.keys()) == 0:
            embed.add_field(name="Pas de prédictions trouvées", value="", inline=False)

        return embed

    def format_output_delete(self, deletion_return: bool, bet_hash: str):
        if deletion_return:
            return f'prédiction {bet_hash} supprimée'
        else:
            return f"aucune prédiction correspondate à l'utilisateur prédiction ou ID de la prédiction incorrect"
        
    def format_output_close(self, closing_return: bool, bet_hash: str):
        if closing_return:
            return f'prédiction {bet_hash} fermée'
        else:
            return f"aucune prédiction correspondate à l'utilisateur prédiction ou ID de la prédiction incorrect"
        
    def format_output_open(self, opening_return: bool, bet_hash: str):
        if opening_return:
            return f'prédiction {bet_hash} ouverte'
        else:
            return f"aucune prédiction correspondate à l'utilisateur prédiction ou ID de la prédiction incorrect"


async def setup(bot):
    await bot.add_cog(Bet(bot))