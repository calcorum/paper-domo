from discord.ext import commands

COGS = [
    'cogs.owner',
    'cogs.helpers',
    'cogs.admins',
    'cogs.economy',
    'cogs.players',
]

bot = commands.Bot(command_prefix='.',
                   description='The Paper Dynasty Bot\nIf you have questions, feel free to contact Cal.',
                   case_insensitive=True,
                   owner_id=258104532423147520)


@bot.event
async def on_ready():
    print('Logged in as:')
    print(bot.user.name)
    print(bot.user.id)
    print('------')


for c in COGS:
    try:
        bot.load_extension(c)
        print(f'Loaded cog: {c}')
    except Exception as e:
        print(f'******\nFailed to load cog: {c}')
        print(f'{type(e).__name__} - {e}')
        print('******')
    print('------')


bot.run("NzExNjQ5NTU3NTQ0NDM1ODAz.XuQyEA.8PlXny6zGqj2iHg6R38BcYuBazg")
