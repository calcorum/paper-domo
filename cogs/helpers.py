import discord
import asyncio
from db_engine import *
from discord.ext import commands


class Helpers(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def send_to_bothole(self, ctx, content, embed):
        await discord.utils.get(ctx.guild.text_channels, name='pd-bot-hole') \
            .send(content=content, embed=embed)

    async def send_to_news(self, ctx, content, embed):
        await discord.utils.get(ctx.guild.text_channels, name='pd-news-ticker') \
            .send(content=content, embed=embed)

    async def get_player_embed(self, player):
        if player.rarity.name == 'Replacement':
            embed = discord.Embed(title=f'{player.cardset} {player.name}',
                                  color=0xe6b0aa)
        elif player.rarity.name == 'Reserve':
            embed = discord.Embed(title=f'{player.cardset} {player.name}',
                                  color=0xf6ddcc)
        elif player.rarity.name == 'Starter':
            embed = discord.Embed(title=f'{player.cardset} {player.name}',
                                  color=0xb7d5b5)
        elif player.rarity.name == 'All-Star':
            embed = discord.Embed(title=f'{player.cardset} {player.name}',
                                  color=0x5ecc57)
        else:
            embed = discord.Embed(title=f'{player.cardset} {player.name}',
                                  color=0x56f1fa)

        owned_by = Card.select(Card.team).where(Card.player == player).distinct().count()

        embed.add_field(name='Rarity', value=f'{player.rarity}')
        embed.add_field(name='Card Set', value=f'{player.cardset}')
        embed.add_field(name='Team/Position', value=f'{player.mlbclub} {player.primary}')
        embed.add_field(name='Owned By', value=f'{owned_by} Team{"s" if owned_by != 1 else ""}')
        embed.set_image(url=player.url)

        return embed

    async def typing_pause(self, ctx, seconds=1):
        async with ctx.typing():
            await asyncio.sleep(seconds)

    async def pause_then_type(self, ctx, message):
        async with ctx.typing():
            await asyncio.sleep(len(message) / 100)
            await ctx.send(message)

    async def check_if_pdhole(self, ctx):
        if ctx.message.channel.name != 'pd-bot-hole':
            await ctx.send('Slide on down to my bot-hole for running commands.')
            await ctx.message.add_reaction('❌')
            return False
        return True

    def get_sorted_collection(self, team):
        try:
            all_cards = Card.select().where(Card.team == team)
            sorted_cards = sorted(all_cards, key=lambda x: x.player, reverse=True)
            return sorted_cards
        except Exception as e:
            print(f'**ERROR** sorting collection: {e}')
            return False

    def get_team_value(self, team):
        try:
            team_value = 0
            unopened_packs = (Pack
                              .select()
                              .where((Pack.team == team) & (Pack.card1.is_null())))

            team_value += unopened_packs.count() * 5
            all_cards = self.get_sorted_collection(team)
            for x in all_cards:
                if x.player.rarity.name == 'MVP':
                    team_value += 5
                elif x.player.rarity.name == 'All-Star':
                    team_value += 3
                elif x.player.rarity.name == 'Starter':
                    team_value += 2
                elif x.player.rarity.name == 'Reserve':
                    team_value += 1
            return team_value
        except Exception as e:
            print(f'**ERROR** getting team value: {e}')
            return False

    def get_roster_sheet(self, team):
        return 'boobs'
        return f'https://docs.google.com/spreadsheets/d/{team.gsheet}/edit'

    def get_active_roster(self, team, avatarurl):
        roster_list = Roster.get_cards(team)

        tp_query = (Pack
                    .select()
                    .where((Pack.team == team) & (Pack.card1.is_null())))
        total_packs_query = (Pack
                             .select()
                             .where(Pack.team == team))

        str_sp = ''
        str_rp = ''
        str_if = ''
        str_of = ''
        for x in roster_list:
            if x.player.primary == 'SP':
                str_sp += f'{x.player.cardset} {x.player.name} ({x.player.primary})\n'
            if x.player.primary == 'RP' or x.player.primary == 'CP':
                str_rp += f'{x.player.cardset} {x.player.name} ({x.player.primary})\n'
            if x.player.primary == 'C' or x.player.primary == '1B' or x.player.primary == '2B' or \
                    x.player.primary == '3B' or x.player.primary == 'SS':
                str_if += f'{x.player.cardset} {x.player.name} ({x.player.primary})\n'
            if x.player.primary == 'LF' or x.player.primary == 'CF' or x.player.primary == 'RF' or x.player.primary == 'DH':
                str_of += f'{x.player.cardset} {x.player.name} ({x.player.primary})\n'

        embed = discord.Embed(title=f'{team.lname} Starting Roster')
        embed.set_thumbnail(url=f'{avatarurl}')
        embed.add_field(name='General Manager', value=f'{team.gmname}', inline=False)
        embed.add_field(name='Collection Value', value=f'{self.get_team_value(team)}', inline=False)
        embed.add_field(name='Total Packs (Unopen)',
                        value=f'{total_packs_query.count()} ({tp_query.count()})',
                        inline=False)
        embed.add_field(name='Starting Pitchers', value=str_sp, inline=False)
        embed.add_field(name='Relief Pitchers', value=str_rp, inline=False)
        embed.add_field(name='Infielders', value=str_if, inline=False)
        embed.add_field(name='Outfielders', value=str_of, inline=False)
        embed.add_field(name='Roster Sheet', value=self.get_roster_sheet(team), inline=False)
        return embed


def setup(bot):
    bot.add_cog(Helpers(bot))
