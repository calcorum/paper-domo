import math
import discord
import asyncio
import datetime
import pygsheets
from db_engine import *
from discord.ext import commands


class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cheat_time = {}
        self.logging = True
        self.helpers = self.bot.get_cog('Helpers')

    @commands.command(name='give', help='Admin command to grant card packs')
    @commands.is_owner()
    async def give_command(self, ctx, team_abbrev: str, num=1):
        team = Team.get_or_none(Team.abbrev == team_abbrev)
        if team:
            team_packs = self.give_pack(team, num)
            await ctx.send(f'Just gave {num} pack{"s" if num > 1 else ""} to {team.sname}. '
                           f'They now have {team_packs} pack{"s" if team_packs > 1 else ""}.')
        elif team_abbrev == 'LEAGUE':
            await ctx.send(f'Ohhh, snap! Errybody getting a little somethin somethin.')
            for x in Team.select():
                print(f'Team: {x}')
                self.give_pack(x, num)

    @give_command.error
    async def give_command_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            await ctx.message.add_reaction('🖕')

    @commands.command(name='open', help='Open up one of your card packs!')
    @commands.has_any_role('Paper Dynasty Players')
    async def open_command(self, ctx, *pack_id):
        if ctx.message.channel.name != 'pd-bot-hole':
            await ctx.send('Slide on down to my bot-hole for running commands.')
            await ctx.message.add_reaction('❌')
            return

        if pack_id:
            this_pack = Pack.get_or_none(Pack.id == pack_id)
        else:
            team = Team.get_by_owner(ctx.author.id)
            if not team:
                await ctx.send(f'You...do I know you? I don\'t think I do. Go on and git.')
                return
            try:
                this_pack = Pack.get((Pack.team == team) & (Pack.card1.is_null()))
            except Exception as e:
                print(f'Could not find unoped pack for {team.gmname} - {e}')
                await ctx.send(f'It doesn\'t look like you have any unopened packs. '
                               f'If you do, let an adult know...maybe I lost it.')
                return

        if not this_pack:
            await ctx.send(f'Hmm...I couldn\'t find pack #{pack_id}.')
            return

        if not await self.expand_pack(ctx, this_pack.team, this_pack):
            await ctx.send(f'Oh, no. This is bad. This is really, really...well not great. Can you find me an adult?')
            return

        overwrites = {ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                      ctx.author: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                      discord.utils.get(ctx.guild.roles, name='Paper Dynasty Players'):
                          discord.PermissionOverwrite(read_messages=True, send_messages=False),
                      ctx.guild.me: discord.PermissionOverwrite(read_messages=True)}
        op_ch = await ctx.guild.create_text_channel(
            f'{this_pack.team.abbrev.lower()}-pack{this_pack.id}-opening',
            overwrites=overwrites,
            category=discord.utils.get(ctx.guild.categories, name='Paper Dynasty Openings')
        )

        cards = [this_pack.card1, this_pack.card2, this_pack.card3,
                 this_pack.card4, this_pack.card5, this_pack.card6]

        await op_ch.send(f'{ctx.author.mention} - let\'s take a look at these cards...')
        for x in cards:
            await asyncio.sleep(5)
            await self.present_player(ctx, op_ch, x)

        await self.helpers.pause_then_type(op_ch, f'I will clear out this channel in 5 minutes.')
        if team.gsheet:
            await self.helpers.pause_then_type(op_ch, 'Updating your google sheet now...')
            async with ctx.typing():
                if await self.write_collection(op_ch, team, extra=0):
                    await self.helpers.pause_then_type(op_ch, 'All done!')
        await asyncio.sleep(240)
        await op_ch.send(f'1 minute left before this channel goes away.')
        await asyncio.sleep(60)
        await op_ch.delete()

    @commands.command(name='comeonmanineedthis', help='You need help')
    @commands.has_any_role('Paper Dynasty Players')
    async def cheat_pack(self, ctx):
        if ctx.message.channel.name != 'pd-bot-hole':
            await ctx.send('Slide on down to my bot-hole for running commands.')
            await ctx.message.add_reaction('❌')
            return

        team = Team.get_by_owner(ctx.author.id)
        if not team:
            await ctx.send(f'You...do I know you? I don\'t think I do. Go on and git.')
            return
        if team.abbrev not in self.cheat_time.keys():
            self.cheat_time[team.abbrev] = datetime.datetime.now()
            await ctx.send(f'Alright, you look like you could use a little somethin. Take a pack. '
                           f'Come back in 20 minutes ;)')
            self.give_pack(team, 1)
        else:
            delta = datetime.datetime.now() - self.cheat_time[team.abbrev]
            if delta.total_seconds() < 1200:
                minutes = 20 - math.floor((delta.seconds % 3600) / 60)
                await ctx.message.add_reaction('❌')
                await ctx.send(f'You\'ve got {minutes} minute{"s" if minutes > 1 else ""} before your next pull. '
                               f'You\'ll be fine, though. Just take a deep breath and see '
                               f'if anybody else can open one.')
            else:
                self.cheat_time[team.abbrev] = datetime.datetime.now()
                await ctx.send(f'Alright, you look like you could use a little somethin. Take a pack. '
                               f'Come back in 20 minutes ;)')
                self.give_pack(team, 1)
        print(f'now cheat time: {self.cheat_time}')

    @commands.command(name='newteam', help='IN TESTING, get a sample starter team')
    @commands.has_any_role('Paper Dynasty Players')
    async def starter_team(self, ctx):
        if ctx.message.channel.name != 'pd-bot-hole':
            await ctx.send('Slide on down to my bot-hole for running commands.')
            await ctx.message.add_reaction('❌')
            return

        logging = True

        owner_team = Team.get_by_owner(ctx.author.id)
        # New team survey
        if owner_team:
            await ctx.send(f'Whoa there, bucko. I already have you down as GM of the {owner_team.sname}.')
            return
        else:
            def abbrev_check(mes):
                return mes.author == ctx.author and 3 >= len(mes.content) >= 2 and mes.content.isalpha()

            def name_check(mes):
                return mes.author == ctx.author and len(mes.content) <= 40

            overwrites = {ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                          ctx.author: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                          ctx.guild.me: discord.PermissionOverwrite(read_messages=True)}
            op_ch = await ctx.guild.create_text_channel(
                f'hello-{ctx.author.name}',
                overwrites=overwrites,
                category=discord.utils.get(ctx.guild.categories, name='Paper Dynasty Openings')
            )
            try:
                await self.helpers.pause_then_type(
                    op_ch,
                    f'Oh, hi, {ctx.author.mention}! I am Paper Domo and I am going to get you all set up. '
                    f'First, what is your name?')
                new_gmname = await self.bot.wait_for('message', check=name_check, timeout=30.0)
                new_gmname = new_gmname.content.replace('"', '')

                await self.helpers.pause_then_type(op_ch, f'Alrighty, {new_gmname}, what would you like your team\'s '
                                           f'2 or 3 letter abbreviation to be?')
                new_abbrev = await self.bot.wait_for('message', check=abbrev_check, timeout=30.0)
                new_abbrev = new_abbrev.content.replace('"', '')

                await self.helpers.pause_then_type(op_ch,
                                      f'Got it! What is the full name of {new_abbrev}? '
                                      f'Something like "Milwaukee Brewers" or "Baltimore Orioles".')
                new_lname = await self.bot.wait_for('message', check=name_check, timeout=30.0)
                new_lname = new_lname.content.replace('"', '')
                if new_lname == new_gmname or new_lname == new_abbrev:
                    await self.helpers.pause_then_type(op_ch,
                                          'Let\'s try this again. Your team name can\'t match your name '
                                          'or team abbreviation.')

                await self.helpers.pause_then_type(op_ch,
                                      f'Well that is a mouthful. What would {new_abbrev}\'s short name be? '
                                      f'Something like "Black Bears", "Angels", or "Crabbers".')
                new_sname = await self.bot.wait_for('message', check=name_check, timeout=30.0)
                new_sname = new_sname.content.replace('"', '')
                if new_sname == new_gmname or new_sname == new_abbrev:
                    await self.helpers.pause_then_type(
                        op_ch,
                        'Let\'s try this again. Your team name can\'t match your name or team abbreviation.')
                    return
                owner_team = Team(abbrev=new_abbrev, sname=new_sname, lname=new_lname, gmid=ctx.author.id,
                                  gmname=new_gmname, weeklyclaim=False, dailyclaim=False,
                                  weeklypacks=0, season=1)

                await self.helpers.pause_then_type(
                    op_ch,
                    f'Noice. I\'ve got you down as the {new_sname}. Let\'s get you a starter team. '
                    f'What MLB club would you like to use as your anchor?'
                )
                choice_response = await self.bot.wait_for('message', check=name_check, timeout=30.0)

                await self.helpers.typing_pause(ctx, 1)
            except TimeoutError:
                await op_ch.send('Welp, I have to go. If you want to try setting up your team again, hit me up.')
                await asyncio.sleep(60)
                await op_ch.delete()
                return
            except Exception as e:
                await op_ch.send('Welp, I have to go. If you want to try setting up your team again, hit me up.')
                await asyncio.sleep(60)
                await op_ch.delete()
                return

        # Get team
        team_flag = False
        all_teams = {
            'Arizona Diamondbacks': ['ARI', 'Diamondbacks'],
            'Atlanta Braves': ['ATL', 'Braves'],
            'Baltimore Orioles': ['BAL', 'Orioles'],
            'Boston Red Sox': ['BOS', 'Red Sox'],
            'Chicago Cubs': ['CHC', 'Cubs'],
            'Chicago White Sox': ['CHW', 'White Sox'],
            'Cincinnati Reds': ['CIN', 'Reds'],
            'Cleveland Indians': ['CLE', 'Indians'],
            'Colorado Rockies': ['COL', 'Rockies'],
            'Detroit Tigers': ['DET', 'Tigers'],
            'Houston Astros': ['HOU', 'Astros'],
            'Kansas City Royals': ['KCR', 'Royals'],
            'Los Angeles Angels': ['LAA', 'CAL', 'Angels'],
            'Los Angeles Dodgers': ['LAD', 'Dodgers'],
            'Miami Marlins': ['MIA', 'Marlins'],
            'Milwaukee Brewers': ['MIL', 'MKE', 'Brewers'],
            'Minnesota Twins': ['MIN', 'Twins'],
            'New York Mets': ['NYM', 'Mets'],
            'New York Yankees': ['NYY', 'Yankees'],
            'Oakland Athletics': ['OAK', 'Athletics'],
            'Philadelphia Phillies': ['PHI', 'Phillies'],
            'Pittsburgh Pirates': ['PIT', 'Pirates'],
            'San Diego Padres': ['SDP', 'Padres'],
            'Seattle Mariners': ['SEA', 'Mariners'],
            'San Francisco Giants': ['SFG', 'Giants'],
            'St Louis Cardinals': ['STL', 'Cardinals'],
            'Tampa Bay Rays': ['TBR', 'Rays'],
            'Texas Rangers': ['TEX', 'Rangers'],
            'Toronto Blue Jays': ['TOR', 'Jays'],
            'Washington Nationals': ['WSN', 'Nationals'],
        }

        if choice_response.content.title() in all_teams.keys():
            team_choice = choice_response.content
        else:
            for x in all_teams:
                if choice_response.content.upper() in all_teams[x]:
                    team_choice = x
                    break
                if choice_response.content.title() in all_teams[x]:
                    team_choice = x
                    break
            else:
                await op_ch.send('Ope. I don\'t recognize that team. I try to recognize abbreviations (BAL), '
                                 'short names (Orioles), and long names ("Baltimore Orioles"). If you have to enter '
                                 'a space, put quotes around the team name ("Red Sox").')
                return

        print(team_choice) if logging else True

        team_allstars = Player.select().join(Rarity)\
            .where((Player.mlbclub == team_choice) &
                   (Player.rarity == Rarity.get(Rarity.name == 'All-Star')) &
                   (Player.primary != 'RP'))\
            .order_by(fn.Random())
        team_starters = Player.select().join(Rarity)\
            .where((Player.mlbclub == team_choice) &
                   (Player.rarity == Rarity.get(Rarity.name == 'Starter')) &
                   (Player.primary != 'RP'))\
            .order_by(fn.Random())

        print(f'AS count: {team_allstars.count()}\nSta count: {team_starters.count()}') if logging else True

        # Get anchor players
        roster_counts = {
            'SP': 0,
            'RP': 0,
            'C': 0,
            '1B': 0,
            '2B': 0,
            '3B': 0,
            'SS': 0,
            'LF': 0,
            'CF': 0,
            'RF': 0,
            'DH': 0,
            'Reserve': 0,
            'Replacement': 0,
        }
        roster_list = []
        anchor_starters = ''
        if team_allstars.count() > 0:
            # Get anchor team All-Star
            anchor_allstar = None
            for x in team_allstars:
                anchor_allstar = x
                roster_list.append(x)
                roster_counts[x.primary] += 1
                break
            print(f'Anchor: {anchor_allstar}') if logging else True

            # Get two starters
            starter_pool = Player.select().join(Rarity)\
                .where(Player.rarity == Player.rarity == Rarity.get(Rarity.name == 'Starter'))\
                .order_by(fn.Random()).limit(8)
            count = 0
            for x in starter_pool:
                if roster_counts[x.primary] == 0:
                    roster_list.append(x)
                    roster_counts[x.primary] += 1
                    anchor_starters += f'{x}\n'
                    print(f'Anchor starter: {x}') if logging else True
                    count += 1
                    if count > 1:
                        break
        elif team_starters.count() > 1:
            # Get two starters
            print(f'anchor pool: {team_starters}') if logging else True
            for x in team_starters:
                if roster_counts[x.primary] == 0:
                    roster_list.append(x)
                    roster_counts[x.primary] += 1
                    print(f'Anchor starter: {x}') if logging else True
                    anchor_starters += f'{x}\n'
                    if len(roster_list) >= 2:
                        break

            # Get anchor All-Star
            anchor_allstar = Player.select().join(Rarity)\
                .where((Player.rarity == Player.rarity == Rarity.get(Rarity.name == 'All-Star')) &
                       (Player.primary != "RP") &
                       (Player.primary != "CP"))\
                .order_by(fn.Random()).limit(5)
            for x in anchor_allstar:
                if roster_counts[x.primary] == 0:
                    anchor_allstar = x
                    roster_list.append(x)
                    roster_counts[x.primary] += 1
                    print(f'Anchor All-Star: {x}') if logging else True
                    break
        else:
            await ctx.send(f'It pains me to say this, but the {team_choice} don\'t have an All-Star nor do they '
                           f'have two starters to seed your team. Please select another team.')
            return
        print(f'Post anchor roster comp: {roster_counts}') if logging else True

        embed = discord.Embed(title=f'{team_choice} Anchors')
        embed.add_field(name='All-Star', value=f'{anchor_allstar}', inline=False)
        embed.add_field(name='Starters',
                        value=anchor_starters, inline=False)
        embed.set_image(url=f'{anchor_allstar.url}')
        await op_ch.send(content=f'{ctx.author.mention}', embed=embed)

        # Get 5 SP
        random_sp = (Player
                     .select()
                     .join(Rarity)
                     .where((Player.primary == 'SP') &
                            ((Player.rarity == Rarity.get(Rarity.name == 'Replacement')) |
                             (Player.rarity == Rarity.get(Rarity.name == 'Reserve'))))
                     .order_by(fn.Random())
                     .limit(15))
        count = 0
        for x in random_sp:
            if x not in roster_list:
                roster_list.append(x)
                roster_counts[x.primary] += 1
                roster_counts[x.rarity.name] += 1
                count += 1
            if count > 5:
                break

        # Get 5 RP
        random_rp = (Player
                     .select()
                     .join(Rarity)
                     .where(((Player.primary == 'RP') | (Player.primary == 'CP')) &
                            ((Player.rarity == Rarity.get(Rarity.name == 'Replacement')) |
                             (Player.rarity == Rarity.get(Rarity.name == 'Reserve'))))
                     .order_by(fn.Random())
                     .limit(15))
        count = 0
        for x in random_rp:
            if x not in roster_list:
                roster_list.append(x)
                roster_counts[x.primary] += 1
                roster_counts[x.rarity.name] += 1
                count += 1
            if count > 5:
                break

        # Ensure all positions have two players
        for pos in roster_counts.keys():
            print(f'Starting {pos}') if logging else True
            if pos == 'DH' or pos == 'Reserve' or pos == 'Replacement':
                pass
            else:
                print(f'{pos} Count: {roster_counts[pos]}') if logging else True
                while roster_counts[pos] < 2:
                    random_draw = (Player
                                   .select()
                                   .where((Player.primary == pos) &
                                          ((Player.rarity == Rarity.get(Rarity.name == 'Replacement')) |
                                           (Player.rarity == Rarity.get(Rarity.name == 'Reserve'))))
                                   .order_by(fn.Random())
                                   .limit(15))
                    print(f'Replacement count: {roster_counts["Replacement"]}') if logging else True
                    if roster_counts['Replacement'] >= 15:
                        for x in random_draw:
                            if x.rarity.name == 'Reserve':
                                roster_list.append(x)
                                roster_counts[x.rarity.name] += 1
                                roster_counts[pos] += 1
                                break
                    elif roster_counts['Reserve'] >= 12:
                        for x in random_draw:
                            if x.rarity.name == 'Replacement':
                                roster_list.append(x)
                                roster_counts[x.rarity.name] += 1
                                roster_counts[pos] += 1
                                break
                    elif roster_counts['Reserve'] < 12 and roster_counts['Replacement'] < 15:
                        roster_list.append(random_draw[0])
                        roster_counts[random_draw[0].rarity.name] += 1
                        roster_counts[pos] += 1
                    print(f'Adding {pos}: {roster_list[-1]}') if logging else True
                    print(f'{pos} Count: {roster_counts[pos]}') if logging else True

        print(f'roster_count: {roster_counts}') if logging else True
        if roster_counts['Reserve'] + roster_counts['Replacement'] < 27:
            random_draw = (Player
                           .select()
                           .where((Player.rarity == Rarity.get(Rarity.name == 'Replacement')) |
                                  (Player.rarity == Rarity.get(Rarity.name == 'Reserve')))
                           .order_by(fn.Random())
                           .limit(15))
            for x in random_draw:
                if x not in roster_list:
                    print(f'Trying to add: {x}')
                    roster_list.append(x)
                    roster_counts[x.rarity.name] += 1
                    roster_counts[x.primary] += 1
                if roster_counts['Reserve'] + roster_counts['Replacement'] >= 27:
                    break

        team_cards = []
        for x in roster_list:
            team_cards.append({
                'player': x,
                'team': owner_team,
            })

        await self.helpers.pause_then_type(
            op_ch, 'I am going to go create your roster sheet. This will take a few seconds.')
        # Create team and starter cards
        async with op_ch.typing():
            sheets = pygsheets.authorize()
            team_roster_sheet = sheets.drive.copy_file(
                '1Z-g3M_rSnRdr-xjXP0YqxMhnOIGsaUK_2v5M3fUODH8',
                f'{owner_team.lname} Roster Sheet',
                '163QSgtsduyFf67A0IWBFvAwYIpHMz_cD')

        owner_team.gsheet = team_roster_sheet['id']
        owner_team.save()
        with db.atomic():
            try:
                for batch in chunked(team_cards, 20):
                    Card.insert_many(batch).execute()
            except Exception as e:
                error = f'**INSERT ERROR (cards):** {type(e).__name__} - {e}'
                print(error)
                await ctx.send(f'Jinkies, guys. I\'ve got an ugly error:\n\n{e}')
                return

        # Create default roster
        try:
            print(f'team_cards[0]: {team_cards[0]}')
            print(f'card 5: {team_cards[5]} / season: {Current.get_by_id(1).season} / team: {owner_team}')
            current_roster = self.helpers.get_sorted_collection(owner_team)
            roster_query = Roster.replace(
                team=owner_team,
                season=Current.get_by_id(1).season,
                card1=current_roster[0],
                card2=current_roster[1],
                card3=current_roster[2],
                card4=current_roster[3],
                card5=current_roster[4],
                card6=current_roster[5],
                card7=current_roster[6],
                card8=current_roster[7],
                card9=current_roster[8],
                card10=current_roster[9],
                card11=current_roster[10],
                card12=current_roster[11],
                card13=current_roster[12],
                card14=current_roster[13],
                card15=current_roster[14],
                card16=current_roster[15],
                card17=current_roster[16],
                card18=current_roster[17],
                card19=current_roster[18],
                card20=current_roster[19],
                card21=current_roster[20],
                card22=current_roster[21],
                card23=current_roster[22],
                card24=current_roster[23],
                card25=current_roster[24],
                card26=current_roster[25],
            )
            print(f'roster_query: {roster_query}')
            roster_query.execute()
        except Exception as e:
            error = f'**INSERT ERROR (rosters):** {type(e).__name__} - {e}'
            print(error)
            await op_ch.send(f'Jinkies, guys. I\'ve got an ugly error:\n\n{e}')
            return

        str_sp = ''
        str_rp = ''
        str_if = ''
        str_of = ''
        for x in roster_list:
            if x.primary == 'SP':
                str_sp += f'{x.cardset} {x.name} ({x.primary})\n'
            if x.primary == 'RP' or x.primary == 'CP':
                str_rp += f'{x.cardset} {x.name} ({x.primary})\n'
            if x.primary == 'C' or x.primary == '1B' or x.primary == '2B' or x.primary == '3B' or x.primary == 'SS':
                str_if += f'{x.cardset} {x.name} ({x.primary})\n'
            if x.primary == 'LF' or x.primary == 'CF' or x.primary == 'RF':
                str_of += f'{x.cardset} {x.name} ({x.primary})\n'

        embed = discord.Embed(title=f'{owner_team.lname} Starting Roster')
        embed.add_field(name='Starting Pitchers', value=str_sp, inline=False)
        embed.add_field(name='Relief Pitchers', value=str_rp, inline=False)
        embed.add_field(name='Infielders', value=str_if, inline=False)
        embed.add_field(name='Outfielders', value=str_of, inline=False)
        embed.add_field(name='Roster Sheet', value=self.helpers.get_roster_sheet(owner_team))
        await op_ch.send(content=None, embed=embed)

        print(f'roster_count: {roster_counts}') if logging else True

        await self.helpers.pause_then_type(op_ch, 'This is your personal bot channel.')
        await self.write_collection(op_ch, owner_team, 0)

        await asyncio.sleep(3600)
        await op_ch.delete()

    @commands.command(name='deleteteam', help='IN TESTING, remove your starter team')
    @commands.has_any_role('Paper Dynasty Players')
    async def delete_team(self, ctx):
        if ctx.message.channel.name != 'pd-bot-hole':
            await ctx.send('Slide on down to my bot-hole for running commands.')
            await ctx.message.add_reaction('❌')
            return

        team = Team.get_by_owner(ctx.author.id)
        if not team:
            await ctx.send('Now you wait just a second. You don\'t have a team!')
            return

        await ctx.send('Are you sure you want to delete your team and full collection?\n\nType \'YES\' to confirm.')

        def confirmation_check(mes):
            return mes.author == ctx.author and mes.content.upper() == 'YES'

        try:
            confirm_resp = await self.bot.wait_for('message', check=confirmation_check, timeout=10.0)
            all_packs = Pack.delete().where(Pack.team == team)
            all_cards = Card.delete().where(Card.team == team)

            all_packs.execute()
            all_cards.execute()
            team.delete_instance()

            await self.helpers.pause_then_type(ctx, 'All done. It\'s like the you were never here.')
        except TimeoutError:
            return

    @commands.command(name='update', help='Pull team from Sheets for cuts and roster update')
    @commands.has_any_role('Paper Dynasty Players')
    async def update_team(self, ctx):
        if not await self.helpers.check_if_pdhole(ctx):
            return

        team = Team.get_by_owner(ctx.author.id)
        if not team:
            await ctx.send('Now you wait just a second. You don\'t have a team!')
            return

        await self.get_collection(ctx, team)

    @staticmethod
    def give_pack(team: Team, num=1):
        for x in range(num):
            new_pack = Pack(team=team)
            new_pack.save()
            print(f'starting weeklypacks: {team.weeklypacks}')
            team.weeklypacks += 1
            team.save()
            print(f'ending weeklypacks: {team.weeklypacks}')
        return Pack.select().where((Pack.team == team) & (Pack.card1.is_null())).count()

    async def present_player(self, ctx, channel, card):
        mvp_flag = False
        if card.player.rarity.name == 'Starter':
            await channel.send(f'Next up from the {card.player.cardset} set...')
            await asyncio.sleep(2)
        elif card.player.rarity.name == 'All-Star':
            await channel.send(f'Now we\'ve got a {card.player.primary} from the {card.player.cardset} set...')
            await asyncio.sleep(2)
            await channel.send(f'He played for the {card.player.mlbclub}...')
            await asyncio.sleep(2)
        elif card.player.rarity.name == 'MVP':
            mvp_flag = True
            await channel.send(f'@here \n'
                               f'Oh wow...this card comes from the {card.player.cardset} set.')
            await asyncio.sleep(2)
            await channel.send(f'This guy played for the {card.player.mlbclub} - maybe you\'ve heard of him...')
            await asyncio.sleep(2)
            await channel.send(f'You\'ve got MVP {card.player.primary}...')
            await asyncio.sleep(2)

        await channel.send(content=None, embed=await self.helpers.get_player_embed(card.player))

        if mvp_flag:
            await self.helpers.send_to_news(
                ctx,
                f'The **{card.team.lname}** just pulled {card.player.cardset} MVP **{card.player.name}** '
                f'of the {card.player.mlbclub}!',
                embed=None
            )

    async def expand_pack(self, ctx, team: Team, pack: Pack):
        pack_pos = []
        card_pack = []
        c1_roll = random.randint(1, 100)
        c2_roll = random.randint(1, 100)
        c3_roll = random.randint(1, 100)
        c4_roll = random.randint(1, 100)
        c5_roll = random.randint(1, 100)
        c6_roll = random.randint(1, 100)

        # Cards 1 - 4: 50% Reserve / 50% Replacement
        # Card 5: 2% All - Star / 28% Starter / 70% Reserve
        # Card 6: 2% MVP / 13% All - Star / 85% Starter

        # Grab card 1
        try:
            if c1_roll > 50:
                rarity = Rarity.get(Rarity.name == 'Reserve')
            else:
                rarity = Rarity.get(Rarity.name == 'Replacement')
            chosen = Player.get_random_or_none(rarity)
            if chosen:
                thiscard = Card(player=chosen, team=team)
                card_pack.append(thiscard)
                if chosen.primary not in pack_pos:
                    pack_pos.append(chosen.primary)
            else:
                await ctx.send(f'Oh, jeez. I made an oopsie with this pack. Please go find me an adult. Now! Please!?')
                return
        except Exception as e:
            print(f'**Error** (create_pack card1): {e}')
            await ctx.send(f'Oh, jeez. I made an oopsie with this pack. Please go find me an adult. Now! Please!?')
            return False

        # Grab card 2
        try:
            if c2_roll > 50:
                rarity = Rarity.get(Rarity.name == 'Reserve')
            else:
                rarity = Rarity.get(Rarity.name == 'Replacement')
            chosen = Player.get_random_or_none(rarity)
            if chosen:
                thiscard = Card(player=chosen, team=team)
                card_pack.append(thiscard)
                if chosen.primary not in pack_pos:
                    pack_pos.append(chosen.primary)
            else:
                await ctx.send(f'Oh, jeez. I made an oopsie with this pack. Please go find me an adult. Now! Please!?')
                return
        except Exception as e:
            print(f'**Error** (create_pack card2): {e}')
            await ctx.send(f'Oh, jeez. I made an oopsie with this pack. Please go find me an adult. Now! Please!?')
            return False

        # Grab card 3
        try:
            if c3_roll > 50:
                rarity = Rarity.get(Rarity.name == 'Reserve')
            else:
                rarity = Rarity.get(Rarity.name == 'Replacement')
            chosen = Player.get_random_or_none(rarity)
            if chosen:
                thiscard = Card(player=chosen, team=team)
                card_pack.append(thiscard)
                if chosen.primary not in pack_pos:
                    pack_pos.append(chosen.primary)
            else:
                await ctx.send(f'Oh, jeez. I made an oopsie with this pack. Please go find me an adult. Now! Please!?')
                return
        except Exception as e:
            print(f'**Error** (create_pack card3): {e}')
            await ctx.send(f'Oh, jeez. I made an oopsie with this pack. Please go find me an adult. Now! Please!?')
            return False

        # Grab card 4
        try:
            if c4_roll > 50:
                rarity = Rarity.get(Rarity.name == 'Reserve')
            else:
                rarity = Rarity.get(Rarity.name == 'Replacement')
            chosen = Player.get_random_or_none(rarity)
            if chosen:
                thiscard = Card(player=chosen, team=team)
                card_pack.append(thiscard)
                if chosen.primary not in pack_pos:
                    pack_pos.append(chosen.primary)
            else:
                await ctx.send(f'Oh, jeez. I made an oopsie with this pack. Please go find me an adult. Now! Please!?')
                return
        except Exception as e:
            print(f'**Error** (create_pack card4): {e}')
            await ctx.send(f'Oh, jeez. I made an oopsie with this pack. Please go find me an adult. Now! Please!?')
            return False

        # Grab card 5
        try:
            if c5_roll > 98:
                rarity = Rarity.get(Rarity.name == 'All-Star')
            elif c5_roll > 70:
                rarity = Rarity.get(Rarity.name == 'Starter')
            else:
                rarity = Rarity.get(Rarity.name == 'Reserve')
            chosen = Player.get_random_or_none(rarity)
            if chosen:
                thiscard = Card(player=chosen, team=team)
                card_pack.append(thiscard)
                if chosen.primary not in pack_pos:
                    pack_pos.append(chosen.primary)
            else:
                await ctx.send(f'Oh, jeez. I made an oopsie with this pack. Please go find me an adult. Now! Please!?')
                return
        except Exception as e:
            print(f'**Error** (create_pack card5): {e}')
            await ctx.send(f'Oh, jeez. I made an oopsie with this pack. Please go find me an adult. Now! Please!?')
            return False

        # Grab card 6
        try:
            if c6_roll > 98:
                rarity = Rarity.get(Rarity.name == 'MVP')
            elif c6_roll > 85:
                rarity = Rarity.get(Rarity.name == 'All-Star')
            else:
                rarity = Rarity.get(Rarity.name == 'Starter')
            chosen = Player.get_random_or_none(rarity)
            if chosen:
                thiscard = Card(player=chosen, team=team)
                card_pack.append(thiscard)
                if chosen.primary not in pack_pos:
                    pack_pos.append(chosen.primary)
            else:
                await ctx.send(f'Oh, jeez. I made an oopsie with this pack. Please go find me an adult. Now! Please!?')
                return
        except Exception as e:
            print(f'**Error** (create_pack card6): {e}')
            await ctx.send(f'Oh, jeez. I made an oopsie with this pack. Please go find me an adult. Now! Please!?')
            return False

        # Save cards
        with db.atomic():
            try:
                for c in card_pack:
                    c.save()
            except Exception as e:
                print(f'**Error** (create_pack insert_cards): {e}')
                await ctx.send(f'Oh, jeez. I made an oopsie with this pack. Please go find me an adult. Now! Please!?')
                return False

        # Save pack
        pack.card1 = card_pack[0]
        pack.card2 = card_pack[1]
        pack.card3 = card_pack[2]
        pack.card4 = card_pack[3]
        pack.card5 = card_pack[4]
        pack.card6 = card_pack[5]
        pack.save()

        return True

    async def get_collection(self, ctx, team):
        await self.helpers.pause_then_type(ctx, 'Let me go check your roster sheet...')

        # Get data from Sheets
        async with ctx.typing():
            sheets = pygsheets.authorize()
            try:
                roster_sheet = sheets.open_by_key(team.gsheet).worksheet_by_title('Full Collection')
                raw_data = roster_sheet.get_values('A2', 'B1000')
            except Exception as e:
                print(f'**ERROR**: {e}')
                await ctx.send(f'Yikes. I need a grown-up to read this. I don\'t know what it means:\n\n{e}')
                return
            else:
                await ctx.send(f'Noice - got it! Give me just a sec to go through it...')

        current_collection = self.helpers.get_sorted_collection(team)
        roster_length_start = len(current_collection)
        rostered_list = []
        cut_list = []
        errors = []
        error_helper = ''

        # Parse raw_data
        try:
            count = 0
            for line in raw_data:
                print(f'Counter: {count}')
                print(f'Line: {line}')
                error_helper = f'row {count + 2}'
                if line[0] != '' and line[1] != '':
                    errors.append(f'You have {current_collection[count].player.name} set to both cut and active '
                                  f'- can only be one or the other.')
                elif line[0] != '':
                    cut_list.append(current_collection[count])
                elif line[1] != '':
                    rostered_list.append(current_collection[count])
                count += 1
        except Exception as e:
            print(f'**ERROR**: {e}')
            await self.helpers.pause_then_type(
                ctx,
                f'Shart. I had an accident. I hate Sheets. Please go get me an adult. I don\'t '
                f'know what this means while I was reading {error_helper}:\n\n{e}')
            return

        if self.logging:
            print(f'Cut List: {cut_list}')
            print(f'Roster List: {rostered_list}')
            print(f'Errors: {errors}')

        # Check for 26 players on the roster
        if len(rostered_list) != 26:
            await self.helpers.pause_then_type(
                ctx,
                f'Will you go double check your roster? You should have 26 rostered players, '
                f'but I see {len(rostered_list)}.')
            return

        # Confirm players to cut with player
        if len(cut_list) > 0:
            cut_message = f'Looks like you want to trade-in the following cards:\n\n'
            tradeins = {'MVP': 0, 'All-Star': 0, 'Starter': 0, 'Reserve': 0, 'Replacement': 0}
            for x in cut_list:
                if x.player.rarity.name == 'MVP':
                    tradeins['MVP'] += 1
                elif x.player.rarity.name == 'All-Star':
                    tradeins['All-Star'] += 1
                elif x.player.rarity.name == 'Starter':
                    tradeins['Starter'] += 1
                elif x.player.rarity.name == 'Reserve':
                    tradeins['Reserve'] += 1
                else:
                    tradeins['Replacement'] += 1
            tradein_value = tradeins["MVP"] * 500 + tradeins["All-Star"] * 50 + tradeins["Starter"] * 5 +\
                            tradeins["Reserve"] * 2 + tradeins["Replacement"]
            cut_message += f'- {tradeins["MVP"]} MVPs: {tradeins["MVP"] * 500} points\n' \
                           f'- {tradeins["All-Star"]} All-Stars: {tradeins["All-Star"] * 50} points\n' \
                           f'- {tradeins["Starter"]} Starters: {tradeins["Starter"] * 5} points\n' \
                           f'- {tradeins["Reserve"]} Reserves: {tradeins["Reserve"] * 2} points\n' \
                           f'- {tradeins["Replacement"]} Replacements: {tradeins["Replacement"]} points\n'\
                           f'This is worth {tradein_value} points / {int(tradein_value/50)} packs.\n\n' \
                           f'If this is correct, please type \'YES\' to confirm.'
            await self.helpers.pause_then_type(ctx, cut_message)

            def check(mes):
                return mes.author == ctx.author and mes.content.lower() == 'yes'
            try:
                resp = await self.bot.wait_for('message', check=check, timeout=15.0)
                await self.helpers.pause_then_type(ctx, 'They gone!')
                self.give_pack(team, int(tradein_value/50))
            except Exception as e:
                print(f'**ERROR**: {e}')
                await self.helpers.pause_then_type(ctx,
                                                   'I will hold off for now. Let me know if you want to try again.')
                return

        # Delete cut list cards
        for x in cut_list:
            x.team = None
            x.save()

        # Set rostered players
        roster_query = Roster.replace(
            team=team,
            season=Current.get_by_id(1).season,
            card1=rostered_list[0],
            card2=rostered_list[1],
            card3=rostered_list[2],
            card4=rostered_list[3],
            card5=rostered_list[4],
            card6=rostered_list[5],
            card7=rostered_list[6],
            card8=rostered_list[7],
            card9=rostered_list[8],
            card10=rostered_list[9],
            card11=rostered_list[10],
            card12=rostered_list[11],
            card13=rostered_list[12],
            card14=rostered_list[13],
            card15=rostered_list[14],
            card16=rostered_list[15],
            card17=rostered_list[16],
            card18=rostered_list[17],
            card19=rostered_list[18],
            card20=rostered_list[19],
            card21=rostered_list[20],
            card22=rostered_list[21],
            card23=rostered_list[22],
            card24=rostered_list[23],
            card25=rostered_list[24],
            card26=rostered_list[25],
        )
        roster_query.execute()

        await ctx.send('Okay, I will note these changes on your Sheet now. Please hold...')
        async with ctx.typing():
            if await self.write_collection(ctx, team, extra=len(cut_list)):
                await self.helpers.pause_then_type(ctx, 'There we go - your roster is up to date!')

    async def write_collection(self, ctx, team, extra):
        async with ctx.typing():
            sheets = pygsheets.authorize()
            roster_sheet = sheets.open_by_key(team.gsheet).worksheet_by_title('Full Collection')
            collection = self.helpers.get_sorted_collection(team)
            rostered_cards = Roster.get_cards(team=team)

            write_data = []
            for x in collection:
                write_data.append(['', f'{"x" if x in rostered_cards else ""}',
                                   x.player.rarity.name, x.player.name, x.player.mlbclub, x.player.cardset,
                                   x.player.wara, x.player.primary, x.player.url, x.player.url2, x.player.pos1,
                                   x.player.pos2, x.player.pos3, x.player.pos4, x.player.pos5, x.player.pos6,
                                   x.player.pos7, x.player.pos8])
            for x in range(extra):
                write_data.append(['', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', '', ''])
            try:
                roster_sheet.update_values(
                    crange='A2', values=write_data
                )
            except Exception as e:
                print(f'**ERROR**: {e}')
                await ctx.send('Barf. I tried to write your roster to the sheet and it didn\'t take. Will you go '
                               'get me some help, please?')
                return False
        return True


def setup(bot):
    bot.add_cog(Economy(bot))
