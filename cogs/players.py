import discord
import pygsheets
from db_engine import *
from discord.ext import commands
from difflib import get_close_matches


class Players(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.helpers = self.bot.get_cog('Helpers')

    @commands.command(name='show', aliases=['card', 'player'], help='show <year> <full name>')
    @commands.has_any_role('Paper Dynasty Players')
    async def display_player(self, ctx, cardset, *, name):
        if ctx.message.channel.name != 'pd-bot-hole':
            await ctx.send('Slide on down to my bot-hole for running commands.')
            await ctx.message.add_reaction('❌')
            return

        yp_query = Player.select(Player.name).where(Player.cardset == cardset)
        yearly_players = []
        for x in yp_query:
            yearly_players.append(x.name.lower())

        try:
            great_match = get_close_matches(name.lower(), yearly_players, cutoff=0.75)[0]
            this_guy = Player.get((fn.Lower(Player.name) == great_match.lower()), Player.cardset == cardset)

            embed = await self.helpers.get_player_embed(this_guy)

            await self.helpers.send_to_bothole(ctx, None, embed)

        except Exception as e:
            await ctx.send(f'I could not find {name.title()}. Is that the right year?')
            print(f'**ERROR** (display_player): {e}')

    @commands.command(name='roster', aliases=['team'], help='Show your active roster')
    @commands.has_any_role('Paper Dynasty Players')
    async def get_inventory(self, ctx, *abbrev):
        if ctx.message.channel.name != 'pd-bot-hole':
            await ctx.send('Slide on down to my bot-hole for running commands.')
            await ctx.message.add_reaction('❌')
            return

        if abbrev:
            team = Team.get_or_none(Team.abbrev == abbrev[0].upper())
            if not team:
                await ctx.send(f'I couldn\'t find **{abbrev}**. Is that the team\'s abbreviation?')
                return
        else:
            team = Team.get_by_owner(ctx.author.id)
            if not team:
                await ctx.send(f'What team are you searching for?')
                return

        embed = self.helpers.get_active_roster(team, f'{self.bot.get_user(team.gmid).avatar_url}')

        await self.helpers.send_to_bothole(ctx, content=f'{ctx.author.mention}', embed=embed)

    @commands.command(name='in', help='Get Paper Dynasty Players role')
    async def give_role(self, ctx, *args):
        await ctx.author.add_roles(discord.utils.get(ctx.guild.roles, name='Paper Dynasty Players'))
        await ctx.send('I got u, boo. ;)')

    @commands.command(name='out', help='Remove Paper Dynasty Players role')
    @commands.has_any_role('Paper Dynasty Players')
    async def take_role(self, ctx, *args):
        await ctx.author.remove_roles(discord.utils.get(ctx.guild.roles, name='Paper Dynasty Players'))
        await ctx.send('Oh no! I\'m so sad to see you go! What are we going to do without you?')

    @commands.command(name='teams', help='List all teams')
    @commands.has_any_role('Paper Dynasty Players')
    async def list_teams(self, ctx, *args):
        if ctx.message.channel.name != 'pd-bot-hole':
            await ctx.send('Slide on down to my bot-hole for running commands.')
            await ctx.message.add_reaction('❌')
            return

        all_teams = Team.select()

        # Collect rarity objects
        try:
            rar_mvp = Rarity.get(Rarity.name == 'MVP')
            rar_als = Rarity.get(Rarity.name == 'All-Star')
            rar_sta = Rarity.get(Rarity.name == 'Starter')
            rar_res = Rarity.get(Rarity.name == 'Reserve')
            rar_rpl = Rarity.get(Rarity.name == 'Replacement')
        except Exception as e:
            print(f'**Error**: (players inv getrars) - {e}')
            return

        embed = discord.Embed(title='All Teams', color=0xdeeadd)

        # Build embed
        for x in all_teams:
            mvps, alss, stas, ress, reps = 0, 0, 0, 0, 0
            roster = Roster.get_cards(team=x)

            for p in roster:
                if p.player.rarity == rar_mvp:
                    mvps += 1
                elif p.player.rarity == rar_als:
                    alss += 1
                elif p.player.rarity == rar_sta:
                    stas += 1
                elif p.player.rarity == rar_res:
                    ress += 1
                else:
                    reps += 1

            un_packs = Pack.select(Pack.id).where((Pack.team == x) & (Pack.card1.is_null())).count()
            op_packs = Pack.select(Pack.id).where((Pack.team == x) & (Pack.card1.is_null(False))).count()

            embed.add_field(
                name=f'{x.lname}',
                value=f'GM: {x.gmname}\n'
                      f'Packs (Unopen): {op_packs + un_packs} ({un_packs})\n\n'
                      f'MVPs: {mvps}\n'
                      f'All-Stars: {alss}\n'
                      f'Starters: {stas}\n'
                      f'Reserves: {ress}\n'
                      f'Replacements: {reps}\n------\n'
                      f'Collection Value: {self.helpers.get_team_value(x)}')

        await self.helpers.send_to_bothole(ctx, content=f'{ctx.author.mention}', embed=embed)

    @commands.command(name='result', help='Log your game results')
    @commands.has_any_role('Paper Dynasty Players')
    async def result(self, ctx, awayabbrev: str, awayscore: int, homeabbrev: str, homescore: int):
        # Validate teams listed
        try:
            awayteam = Team.get(Team.abbrev == awayabbrev.upper())
            hometeam = Team.get(Team.abbrev == homeabbrev.upper())
            print(f'Final: {awayabbrev} {awayscore} - {homescore} {homeabbrev}')
        except Exception as e:
            error = f'**ERROR:** {type(e).__name__} - {e}'
            print(error)
            await ctx.message.add_reaction('❌')
            await ctx.send(f'Hey, {ctx.author.mention}, I couldn\'t find the teams you mentioned. You put '
                           f'**{awayabbrev}** as the away team and **{homeabbrev}** as the home team.')
            return

        earnings = {'away': 0, 'home': 0}
        earnings_away = []
        earnings_home = []

        # Check author then log result
        if ctx.author.id in [awayteam.gmid, awayteam.gmid2, hometeam.gmid, hometeam.gmid2] \
                or ctx.author.id == self.bot.owner_id:
            this_result = Result(week=Current.get_by_id(1).week,
                                 awayteam=awayteam, hometeam=hometeam,
                                 awayscore=awayscore, homescore=homescore,
                                 season=Current.get_by_id(1).season)
            this_result.save()
            await self.helpers.pause_then_type(ctx, f'Just logged {awayteam.abbrev.upper()} {awayscore} - '
                                       f'{homescore} {hometeam.abbrev.upper()}')
            await ctx.message.add_reaction('✅')

        # Credit pack for win
        if awayscore > homescore:
            earnings['away'] += 1
            earnings_away.append('- 1 pack for the win\n')
        else:
            earnings['home'] += 1
            earnings_home.append('- 1 pack for the win\n')

        away_team_value = self.helpers.get_team_value(awayteam)
        home_team_value = self.helpers.get_team_value(hometeam)
        delta = away_team_value - home_team_value
        if delta < 0:
            increments = divmod(-delta, self.helpers.TEAM_DELTA_CONSTANT)
            print(f'increments: {increments}')
            packs = min(increments[0], 5)
            if packs > 0:
                earnings['away'] += packs
                earnings_away.append(f'- {packs} pack{"s" if packs > 1 else ""} for underdog\n')
        else:
            increments = divmod(delta, self.helpers.TEAM_DELTA_CONSTANT)
            print(f'increments: {increments}')
            packs = min(increments[0], 5)
            if packs > 0:
                earnings['home'] += packs
                earnings_home.append(f'- {packs} pack{"s" if packs > 1 else ""} for underdog\n')

        print(f'earn away: {earnings["away"]} / earn home: {earnings["home"]}')
        away_packs_remaining = Current.get_by_id(1).packlimit - awayteam.weeklypacks
        home_packs_remaining = Current.get_by_id(1).packlimit - hometeam.weeklypacks
        away_final_earnings = away_packs_remaining if away_packs_remaining >= earnings["away"] else earnings["away"]
        home_final_earnings = home_packs_remaining if home_packs_remaining >= earnings["home"] else earnings["home"]
        print(f'away_final_earnings: {away_final_earnings}')
        print(f'home_final_earnings: {home_final_earnings}')

        # TODO: Seems to be giving underdog the square of their earnings
        economy = self.bot.get_cog('Economy')
        if earnings["away"] > 0:
            print(f'away_final_earnings: {away_final_earnings}')
            economy.give_pack(awayteam, away_final_earnings)
        if earnings["home"] > 0:
            print(f'home_final_earnings: {home_final_earnings}')
            economy.give_pack(hometeam, home_final_earnings)

        embed = discord.Embed(title=f'{awayteam.sname} {awayscore} - {homescore} {hometeam.sname}',
                              description='Score Report / Post Game Earnings')
        embed.add_field(name=awayteam.lname,
                        value=f'Team Value: {away_team_value}\n\n'
                              f'**Earn: {earnings["away"]} pack{"s" if earnings["away"] != 1 else ""}**'
                              f' (limit {away_final_earnings})\n'
                              f'{"Summary:" if len(earnings_away) > 0 else ""}\n'
                              f'{earnings_away[0] if len(earnings_away) > 0 else ""}'
                              f'{earnings_away[1] if len(earnings_away) > 1 else ""}',
                        inline=False)
        embed.add_field(name=hometeam.lname,
                        value=f'Team Value: {home_team_value}\n\n'
                              f'**Earn: {earnings["home"]} pack{"s" if earnings["home"] != 1 else ""}**'
                              f' (limit {home_final_earnings})\n'
                              f'{"Summary:" if len(earnings_home) > 0 else ""}\n'
                              f'{earnings_home[0] if len(earnings_home) > 0 else ""}'
                              f'{earnings_home[1] if len(earnings_home) > 1 else ""}',
                        inline=False)
        await self.helpers.send_to_news(ctx, None, embed)

    @commands.command(name='sheet', aliases=['google'], help='Link to your roster sheet')
    @commands.has_any_role('Paper Dynasty Players')
    async def get_roster_command(self, ctx):
        if ctx.message.channel.name != 'pd-bot-hole':
            await ctx.send('Slide on down to my bot-hole for running commands.')
            await ctx.message.add_reaction('❌')
            return

        team = Team.get_by_owner(ctx.author.id)
        if not team:
            await ctx.send(f'Do you have a team? I don\'t see your name here...')
            return

        await ctx.send(f'{ctx.author.mention}\n{team.lname} Roster Sheet: <{self.helpers.get_roster_sheet(team)}>')


def setup(bot):
    bot.add_cog(Players(bot))
