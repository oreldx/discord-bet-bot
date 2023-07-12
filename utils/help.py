from discord.ext import commands
from discord import Embed

class MyNewHelp(commands.MinimalHelpCommand):
    async def send_pages(self):
        destination = self.get_destination()
        for page in self.paginator.pages:
            emby = Embed(description=page)
            await destination.send(embed=emby)

