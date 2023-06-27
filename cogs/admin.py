from discord.ext import commands


class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def hello_world(self,  ctx):
        await ctx.send('Hello world!')


async def setup(bot):
    await bot.add_cog(Admin(bot))