import discord
from discord.ext import commands


class Owner(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(hidden=True)
    @commands.is_owner()
    async def load(self, ctx, *, cog: str):
        try:
            self.bot.load_extension(f'cogs.{cog}')
            print(f'Loaded {cog}')
            print('------')
        except Exception as e:
            await ctx.send(f'**ERROR:** {type(e).__name__} - {e}')
        else:
            await ctx.send('**SUCCESS**')

    @commands.command(hidden=True)
    @commands.is_owner()
    async def unload(self, ctx, *, cog: str):
        try:
            self.bot.unload_extension(f'cogs.{cog}')
            print(f'Unloaded {cog}')
            print('------')
        except Exception as e:
            await ctx.send(f'**ERROR:** {type(e).__name__} - {e}')
        else:
            await ctx.send('**SUCCESS**')

    @commands.command(hidden=True)
    @commands.is_owner()
    async def reload(self, ctx, *, cog: str):
        try:
            self.bot.unload_extension(f'cogs.{cog}')
            print(f'Unloaded {cog}')
            self.bot.load_extension(f'cogs.{cog}')
            print(f'Reloaded {cog}')
            print('------')
        except Exception as e:
            await ctx.send(f'**ERROR:** {type(e).__name__} - {e}')
        else:
            await ctx.send('**SUCCESS**')


def setup(bot):
    bot.add_cog(Owner(bot))
