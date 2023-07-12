from discord.ext import commands
from discord import Embed

class MyNewHelp(commands.MinimalHelpCommand):
    async def send_bot_help(self, mapping):
        embed = None
        for cog, commands in mapping.items():
           cog_name = getattr(cog, "qualified_name", "No Category")

           if cog_name == 'Bet':
                embed = Embed(title="Help", description="")
                for c in commands:
                    if c.help:
                        command_signature = self.get_command_signature(c)
                        embed.add_field(name=command_signature, value=c.help, inline=False)
        
        if embed is not None:
            channel = self.get_destination()
            await channel.send(embed=embed)
