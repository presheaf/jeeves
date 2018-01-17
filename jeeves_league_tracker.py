#!/usr/bin/python
# -*- coding: utf-8 -*-
import math

class Player:
    def __init__(self, user, ranking=1500):
        self.user = user
        self.ranking = ranking

    def __str__(self):
        return str(self.user)

    def __lt__(self, other):
        return self.ranking < other.ranking

class Match:

    def __init__(self, reporter, opponent, won):
        self.opponent = opponent
        if won:
            self.winner = reporter
            self.loser = opponent
        else:
            self.winner = opponent
            self.loser = reporter
        self.confirmed = False

    def computeELO(self):
        K=32
        r_w = self.winner.ranking
        r_l = self.loser.ranking
        R_w = math.pow(10, r_w/400.)
        R_l = math.pow(10, r_l/400.)
        s = R_w+R_l
        E_w = R_w/s
        E_l = R_l/s
        self.winner.ranking += K*(1-E_w)
        self.loser.ranking -= K*E_l


class League:

    def __init__(self):
        self.matchID = 0
        self.players = {}
        self.matches = []
        self.unmatches = {}
    
    def add_player(self, player):
        if player not in self.players:
            self.players[player] = Player(player)


    def add_unconfirmed(self, reporter, opponent, won):
        """
        Adds an unconfirmed match, adding the players if they are not already in the system.
        Computes updates to ELO as well.
        """
        self.add_player(reporter)
        self.add_player(opponent)
        self.matchID += 1
        self.unmatches[self.matchID] = Match(self.players[reporter], self.players[opponent], won)
        self.matches.append(self.unmatches[self.matchID])
        self.unmatches[self.matchID].computeELO()
        return self.matchID

    def confirm_match(self, ID, user):
        """
        Checks that this user can confirm this match
        Returns whether match was sucessfully confirmed
        """
        if ID not in self.unmatches or user != self.unmatches[ID].opponent.user:
            return False
        else:
            self.unmatches[ID].confirmed = True
            del self.unmatches[ID]
            return True
    
    def decline_match(self, ID, user):
        """
        Declines a match, removing it from the list of unconfirmed matches, and the list of matches.
        Recomputes ELO.
        """
        if (ID not in self.unmatches or user not in 
                [self.unmatches[ID].winner.user, self.unmatches[ID].loser.user]):
            return False
        else:
            self.matches.remove(self.unmatches[ID])
            del self.unmatches[ID]
            self.recalculate_standings()
            return True


    def return_unconfirmed(self):
        if len(self.unmatches) == 0:
            return "No unconfirmed matches! :smiley:"
        s = "Unconfirmed matches: \n"
        for key in self.unmatches:
            s += "Winner: {winner} - Loser: {loser} - MatchID: {matchID}\n".format(
                    matchID=key, winner=self.unmatches[key].winner,
                    loser=self.unmatches[key].loser)
        return s

    def single_standing(self, user):
        if user not in self.players:
            return None
        return round(self.players[user].ranking)

    def show_standings(self):
        standings = sorted(self.players.values(), reverse=True)
        s = "**Standings:**```\n"
        for player in standings:
            s+= "{player:<30} {ranking} ELO\n".format(player=str(player)+":", ranking=round(player.ranking))
        s += "```"
        return s

    def recalculate_standings(self):
        for match in self.matches:
            match.computeELO()


    


