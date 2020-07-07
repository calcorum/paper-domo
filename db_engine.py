import random
from peewee import *

db = SqliteDatabase('pd_test.db')


class Current(Model):
    season = IntegerField(default=1)
    week = IntegerField(default=1)
    packlimit = IntegerField(default=8)

    class Meta:
        database = db


class Rarity(Model):
    value = IntegerField()
    name = CharField()

    def __str__(self):
        return self.name

    class Meta:
        database = db


class Player(Model):
    id = AutoField(primary_key=True)
    name = CharField()
    mlbclub = CharField()
    cardset = CharField()
    rarity = ForeignKeyField(Rarity)
    wara = FloatField()
    primary = CharField()
    url = CharField()
    url2 = CharField(null=True)
    pos1 = IntegerField()
    pos2 = IntegerField(null=True)
    pos3 = IntegerField(null=True)
    pos4 = IntegerField(null=True)
    pos5 = IntegerField(null=True)
    pos6 = IntegerField(null=True)
    pos7 = IntegerField(null=True)
    pos8 = IntegerField(null=True)

    def __str__(self):
        return f'{self.cardset} {self.name} ({self.rarity.name})'

    def __eq__(self, other):
        if self.cardset == other.cardset and self.name == other.name:
            return True
        else:
            return False

    def __lt__(self, other):
        if self.wara < other.wara:
            return True
        elif self.wara > other.wara:
            return False
        elif self.name < other.name:
            return True
        else:
            return False

    @staticmethod
    def get_random_or_none(rarity: Rarity):
        try:
            return Player.select().where(Player.rarity == rarity).order_by(fn.Random()).limit(1)[0]
        except Exception as e:
            print(f'**Error** (db player get_random): {e}')
            return None

    class Meta:
        database = db


class Team(Model):
    abbrev = CharField()
    sname = CharField()
    lname = CharField()
    gmid = IntegerField()
    gmname = CharField(unique=True)
    gsheet = CharField()
    gmid2 = IntegerField(null=True)
    gmname2 = CharField(null=True)
    weeklyclaim = BooleanField()
    dailyclaim = BooleanField()
    weeklypacks = IntegerField()
    season = IntegerField()

    def __str__(self):
        return f'S{self.season} {self.lname}'

    @staticmethod
    def get_by_owner(gmid, season=1):
        team = Team.get_or_none((Team.gmid == gmid) & (Team.season == season))
        if not team:
            team = Team.get_or_none((Team.gmid2 == gmid) & (Team.season == season))
            if not team:
                return None
        return team

    class Meta:
        database = db


class Card(Model):
    player = ForeignKeyField(Player)
    team = ForeignKeyField(Team, null=True)

    def __str__(self):
        return f'{self.player} - {self.team.sname}'

    class Meta:
        database = db


class Roster(Model):
    team = ForeignKeyField(Team, unique=True)
    season = IntegerField()
    card1 = ForeignKeyField(Card)
    card2 = ForeignKeyField(Card)
    card3 = ForeignKeyField(Card)
    card4 = ForeignKeyField(Card)
    card5 = ForeignKeyField(Card)
    card6 = ForeignKeyField(Card)
    card7 = ForeignKeyField(Card)
    card8 = ForeignKeyField(Card)
    card9 = ForeignKeyField(Card)
    card10 = ForeignKeyField(Card)
    card11 = ForeignKeyField(Card)
    card12 = ForeignKeyField(Card)
    card13 = ForeignKeyField(Card)
    card14 = ForeignKeyField(Card)
    card15 = ForeignKeyField(Card)
    card16 = ForeignKeyField(Card)
    card17 = ForeignKeyField(Card)
    card18 = ForeignKeyField(Card)
    card19 = ForeignKeyField(Card)
    card20 = ForeignKeyField(Card)
    card21 = ForeignKeyField(Card)
    card22 = ForeignKeyField(Card)
    card23 = ForeignKeyField(Card)
    card24 = ForeignKeyField(Card)
    card25 = ForeignKeyField(Card)
    card26 = ForeignKeyField(Card)

    def __str__(self):
        return f'{self.team} Roster'

    @staticmethod
    def get_cards(team):
        this_roster = Roster.get(Roster.team == team)
        return [this_roster.card1, this_roster.card2, this_roster.card3, this_roster.card4, this_roster.card5,
                this_roster.card6, this_roster.card7, this_roster.card8, this_roster.card9, this_roster.card10,
                this_roster.card11, this_roster.card12, this_roster.card13, this_roster.card14, this_roster.card15,
                this_roster.card16, this_roster.card17, this_roster.card18, this_roster.card19, this_roster.card20,
                this_roster.card21, this_roster.card22, this_roster.card23, this_roster.card24, this_roster.card25,
                this_roster.card26]

    class Meta:
        database = db


class Pack(Model):
    id = AutoField(primary_key=True)
    team = ForeignKeyField(Team)
    card1 = ForeignKeyField(Card, null=True)
    card2 = ForeignKeyField(Card, null=True)
    card3 = ForeignKeyField(Card, null=True)
    card4 = ForeignKeyField(Card, null=True)
    card5 = ForeignKeyField(Card, null=True)
    card6 = ForeignKeyField(Card, null=True)

    def __str__(self):
        return f'Pack #{self.id} / Team: {self.team}'

    class Meta:
        database = db


class Special(Model):
    name = CharField()
    short_desc = CharField(null=True)
    url = CharField(null=True)
    long_desc = CharField(null=True)
    active = BooleanField(default=False)

    def __str__(self):
        return f'Special {self.name} / {self.short_desc} / Active: {self.active}'

    class Meta:
        database = db


class Result(Model):
    awayteam = ForeignKeyField(Team)
    hometeam = ForeignKeyField(Team)
    awayscore = IntegerField()
    homescore = IntegerField()
    week = IntegerField()
    season = IntegerField()

    class Meta:
        database = db
