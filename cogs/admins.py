import os
import csv
import discord
from db_engine import *
from discord.ext import commands


class Admins(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.helpers = self.bot.get_cog('Helpers')

        db.connect(reuse_if_open=True)
        db.create_tables([Current, Rarity, Player, Team, Card, Roster, Pack, Special, Result])
        db.close()

    async def cog_load(self):
        await self.bot.change_presence(activity=discord.Game(name='strat: .help'))

    @commands.command(name='refresh')
    @commands.is_owner()
    async def import_players(self, ctx, file='import.csv'):
        rarities = {'MVP': 10, 'All-Star': 7, 'Starter': 5, 'Reserve': 3, 'Replacement': 0}
        war_vals = {
            'SP': {'MVP': 7.44, 'All-Star': 5.76, 'Starter': 3.06, 'Reserve': 1.30},
            'RP': {'MVP': 2.56, 'All-Star': 1.93, 'Starter': 1.03, 'Reserve': 0.37},
            'Pos': {'MVP': 7.76, 'All-Star': 5.50, 'Starter': 3.01, 'Reserve': 1.06},
        }
        for x in rarities.keys():
            check_rar = Rarity.get_or_none(Rarity.name == x)
            if not check_rar:
                new_rar = Rarity(value=rarities[x], name=x)
                new_rar.save()

        curr = Current.get_or_none()
        if not curr:
            new_curr = Current(season=1, week=1, packlimit=8)
            new_curr.save()

        tba_players = []
        if os.path.exists(file):
            with open(file, newline='') as cardfile:
                async with ctx.typing():
                    spamreader = csv.reader(cardfile)
                    for row in spamreader:
                        name = row[0]
                        cardset = row[2]

                        this_guy = Player.get_or_none(Player.name == name, Player.cardset == cardset)
                        flag = False
                        if not this_guy:
                            mlbclub = row[1]
                            cardset = row[2]
                            wara = float(row[3])
                            primary = row[4]
                            url = row[5]
                            if row[6] != '':
                                url2 = row[6]
                            else:
                                url2 = None
                            if row[7] != '':
                                pos1 = row[7]
                            else:
                                pos1 = None
                            if row[8] != '':
                                pos2 = row[8]
                            else:
                                pos2 = None
                            if row[9] != '':
                                pos3 = row[9]
                            else:
                                pos3 = None
                            if row[10] != '':
                                pos4 = row[10]
                            else:
                                pos4 = None
                            if row[11] != '':
                                pos5 = row[11]
                            else:
                                pos5 = None
                            if row[12] != '':
                                pos6 = row[12]
                            else:
                                pos6 = None
                            if row[13] != '':
                                pos7 = row[13]
                            else:
                                pos7 = None
                            if row[14] != '':
                                pos8 = row[14]
                            else:
                                pos8 = None
                            rarity = Rarity.get(Rarity.name == 'Replacement')

                            if primary == 'RP':
                                if wara >= war_vals['RP']['MVP']:
                                    rarity = Rarity.get(Rarity.name == 'MVP')
                                elif wara >= war_vals['RP']['All-Star']:
                                    rarity = Rarity.get(Rarity.name == 'All-Star')
                                elif wara >= war_vals['RP']['Starter']:
                                    rarity = Rarity.get(Rarity.name == 'Starter')
                                elif wara > war_vals['RP']['Reserve']:
                                    rarity = Rarity.get(Rarity.name == 'Reserve')
                            elif primary == 'SP':
                                if wara >= war_vals['SP']['MVP']:
                                    rarity = Rarity.get(Rarity.name == 'MVP')
                                elif wara >= war_vals['SP']['All-Star']:
                                    rarity = Rarity.get(Rarity.name == 'All-Star')
                                elif wara >= war_vals['SP']['Starter']:
                                    rarity = Rarity.get(Rarity.name == 'Starter')
                                elif wara > war_vals['SP']['Reserve']:
                                    rarity = Rarity.get(Rarity.name == 'Reserve')
                            else:
                                if wara >= war_vals['Pos']['MVP']:
                                    rarity = Rarity.get(Rarity.name == 'MVP')
                                elif wara >= war_vals['Pos']['All-Star']:
                                    rarity = Rarity.get(Rarity.name == 'All-Star')
                                elif wara >= war_vals['Pos']['Starter']:
                                    rarity = Rarity.get(Rarity.name == 'Starter')
                                elif wara > war_vals['Pos']['Reserve']:
                                    rarity = Rarity.get(Rarity.name == 'Reserve')

                            tba_players.append({
                                'name': name,
                                'mlbclub': mlbclub,
                                'cardset': cardset,
                                'rarity': rarity,
                                'wara': wara,
                                'primary': primary,
                                'url': url,
                                'pos1': pos1,
                                'pos2': pos2,
                                'pos3': pos3,
                                'pos4': pos4,
                                'pos5': pos5,
                                'pos6': pos6,
                                'pos7': pos7,
                                'pos8': pos8,
                            })
                        else:
                            print(f'Matched: {this_guy.name}')
                            if this_guy.mlbclub != row[1]:
                                print(f'mlbclub: {this_guy.mlbclub} to {row[1]}')
                                this_guy.mlbclub = row[1]
                                flag = True
                            if this_guy.cardset != row[2]:
                                print(f'cardset: {this_guy.cardset} to {row[2]}')
                                this_guy.cardset = row[2]
                                flag = True
                            # if this_guy.wara != row[3]:
                            #     print(f'wara: {this_guy.wara} to {row[3]}')
                            #     this_guy.wara = float(row[3])
                            #     flag = True
                            if this_guy.primary != row[4]:
                                print(f'primary: {this_guy.primary} to {row[4]}')
                                this_guy.primary = row[4]
                                flag = True
                            if this_guy.url != row[5]:
                                print(f'url: {this_guy.url} to {row[5]}')
                                this_guy.url = row[5]
                                flag = True
                            if this_guy.pos1 != row[7]:
                                print(f'pos1: {this_guy.pos1} to {row[7]}')
                                this_guy.pos1 = row[7]
                                flag = True
                            rarity = Rarity.get(Rarity.name == 'Replacement')

                            if this_guy.primary == 'RP':
                                if this_guy.wara >= war_vals['RP']['MVP']:
                                    rarity = Rarity.get(Rarity.name == 'MVP')
                                elif this_guy.wara >= war_vals['RP']['All-Star']:
                                    rarity = Rarity.get(Rarity.name == 'All-Star')
                                elif this_guy.wara >= war_vals['RP']['Starter']:
                                    rarity = Rarity.get(Rarity.name == 'Starter')
                                elif this_guy.wara > war_vals['RP']['Reserve']:
                                    rarity = Rarity.get(Rarity.name == 'Reserve')
                            elif this_guy.primary == 'SP':
                                if this_guy.wara >= war_vals['SP']['MVP']:
                                    rarity = Rarity.get(Rarity.name == 'MVP')
                                elif this_guy.wara >= war_vals['SP']['All-Star']:
                                    rarity = Rarity.get(Rarity.name == 'All-Star')
                                elif this_guy.wara >= war_vals['SP']['Starter']:
                                    rarity = Rarity.get(Rarity.name == 'Starter')
                                elif this_guy.wara > war_vals['SP']['Reserve']:
                                    rarity = Rarity.get(Rarity.name == 'Reserve')
                            else:
                                if this_guy.wara >= war_vals['Pos']['MVP']:
                                    rarity = Rarity.get(Rarity.name == 'MVP')
                                elif this_guy.wara >= war_vals['Pos']['All-Star']:
                                    rarity = Rarity.get(Rarity.name == 'All-Star')
                                elif this_guy.wara >= war_vals['Pos']['Starter']:
                                    rarity = Rarity.get(Rarity.name == 'Starter')
                                elif this_guy.wara > war_vals['Pos']['Reserve']:
                                    rarity = Rarity.get(Rarity.name == 'Reserve')

                            if this_guy.rarity != rarity:
                                this_guy.rarity = rarity
                                flag = True

                            if flag:
                                print(f'Updating {this_guy.name}')
                                this_guy.save()
                                flag = False

                print(f'We have {len(tba_players)} players to update.')
                with db.atomic():
                    try:
                        for batch in chunked(tba_players, 20):
                            Player.insert_many(batch).execute()
                    except Exception as e:
                        print(f'**ERROR** (import_players): {e}')
                        await ctx.send(f'Oof, I ran into an issue importing those players. '
                                       f'This might be ugly:\n\n{e}')
                    finally:
                        num_players = Player.select().count()
                        await ctx.send(f'Alright, I have {num_players} players in the database now.')
        else:
            await ctx.send('Yikes, I could not find the import.csv file.')

    @commands.command(name='tempteam', help='Admin command to add team')
    @commands.is_owner()
    async def add_team(self, ctx, abbrev: str, sname: str, lname: str, gmid: int, gmname: str):
        new_team = Team(abbrev=abbrev,
                        sname=sname,
                        lname=lname,
                        gmid=gmid,
                        gmname=gmname,
                        season=1)

        if new_team.save() == 1:
            await ctx.send(f'Hey {discord.utils.get(ctx.guild.members, id=new_team.gmid).mention}, '
                           f'you are now the GM of the {new_team.lname}!')
        else:
            await ctx.send(f'Nope. They suck and don\'t get a team. It has nothing to do with this stack of '
                           f'errors I got when I tried to create their team.')

    @commands.command(name='rates', help='Check current pull rates')
    @commands.has_any_role('Paper Dynasty Players')
    async def all_card_pulls(self, ctx):
        await self.bot.change_presence(activity=discord.Game(name='strat | .help'))
        total_count = Card.select().count()
        mvp_count = (Card
                     .select()
                     .join(Player)
                     .join(Rarity)
                     .where(Card.player.rarity.value == 10)).count()
        als_count = (Card
                     .select()
                     .join(Player)
                     .join(Rarity)
                     .where(Card.player.rarity.value == 7)).count()
        sta_count = (Card
                     .select()
                     .join(Player)
                     .join(Rarity)
                     .where(Card.player.rarity.value == 5)).count()
        res_count = (Card
                     .select()
                     .join(Player)
                     .join(Rarity)
                     .where(Card.player.rarity.value == 3)).count()
        rep_count = (Card
                     .select()
                     .join(Player)
                     .join(Rarity)
                     .where(Card.player.rarity.value == 0)).count()

        print(total_count)
        embed = discord.Embed(title='Current Pull Rates', color=0x800080)
        embed.add_field(name='Total Pulls', value=f'{total_count}')
        embed.add_field(name='MVPs', value=f'{mvp_count} ({(mvp_count / total_count)*100:.2f}%)\n'
                                           f'Target: 0.33%', inline=False)
        embed.add_field(name='All-Stars', value=f'{als_count} ({(als_count / total_count)*100:.2f}%)\n'
                                                f'Target: 2.50%', inline=False)
        embed.add_field(name='Starters', value=f'{sta_count} ({(sta_count / total_count)*100:.2f}%)\n'
                                               f'Target: 18.83%', inline=False)
        embed.add_field(name='Reserves', value=f'{res_count} ({(res_count / total_count)*100:.2f}%)\n'
                                               f'Target: 45.00%', inline=False)
        embed.add_field(name='Replacements', value=f'{rep_count} ({(rep_count / total_count)*100:.2f}%)\n'
                                                   f'Target: 33.33%', inline=False)
        await ctx.send(content=None, embed=embed)

    @commands.command(name='query', help='Run queries against db')
    @commands.is_owner()
    async def dynamic_query(self, ctx, *, query):
        print(f'Query: {query}')
        result = eval(query)
        print(f'Result: {result}')

        embed = discord.Embed(title='Custom Query')
        embed.add_field(name='Result', value=result)

        await ctx.send(content=None, embed=embed)


def setup(bot):
    bot.add_cog(Admins(bot))
