#!/usr/bin/python
# -*- coding: utf-8 -*-

import json, re, requests, random, time, tweepy, logging, discord, pickle
import sts_wikitrawl as sts
from googleapiclient.discovery import build
from fuzzywuzzy import process, fuzz, utils

from twitter_secrets import CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET
from secrets import GOOGLE_API_KEY, GOOGLE_SEARCH_CX
from ripsave import RIP, SAVED
from customemoji import CUSTOMEMOJI, FACTIONS
from abbreviations import ABBREVIATIONS, SUPERSCRIPTS

#Jeeves will now try to understand Netrunner leagues
from jeeves_league_tracker import League

try:
    from .StringMatcher import StringMatcher as SequenceMatcher
except ImportError:
    from difflib import SequenceMatcher

class JeevesBot:

    lastQuery = None
    lastQueryCounter = 0
    lastQueryImage = False
    leagueResults = 'league_results.pkl'

    def __init__(self, log_file):
        # Logging/Error messages setup
        if log_file is not None:
            logger = logging.getLogger('discord')
            logger.setLevel(logging.INFO)
            handler = logging.FileHandler(filename=log_file, encoding='utf-8', mode='w')
            handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
            logger.addHandler(handler)
            self.logger = logger
        else:
            self.logger = None
        
        # Twitter Setup
        twitterAuth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
        twitterAuth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
        self.twitterAPI = tweepy.API(twitterAuth)

        # Google Setup
        self.googleSearcher = build("customsearch", "v1", developerKey=GOOGLE_API_KEY).cse()

        #NRDB Setup
        self.NRDBGet(None)

        #League setup:
        try:
            with open(self.leagueResults, 'rb') as leagueSave:
                self.league = pickle.load(leagueSave)
            self.print_message('Loading existing league')
        except:
            self.league = League()
            self.print_message('Creating new league')

        # Slay The Spire-setup
        self.STSGet(None)

    def STSGet(self, vals):
        self.print_message('Downloading Slay The Spire info from the official Wiki')
        self.sts_cards, self.sts_card_names = sts.fetchCards()
        self.sts_enemies, self.sts_enemy_names = sts.fetchEnemies()
        self.sts_relics, self.sts_relic_names = sts.fetchRelics()
        return 'Slay The Spire-info updated!'

    def NRDBGet(self, vals):
        self.print_message('Downloading NRDB API')
        nrdburl = "https://netrunnerdb.com/api/2.0/public/"
        cardurl = nrdburl+"cards"
        packurl = nrdburl+"packs"
        cycleurl = nrdburl+"cycles"

        nrdb_card_api = requests.get(cardurl).json()
        nrdb_pack_api = requests.get(packurl).json()
        nrdb_cycle_api = requests.get(cycleurl).json()
        
        self.card_data, self.card_names = self.make_card_dictionaries(nrdb_card_api["data"])
        self.pack_data = nrdb_pack_api["data"]
        self.cycle_data = nrdb_cycle_api["data"]

        self.NRDB_URL_TEMPLATE = nrdb_card_api["imageUrlTemplate"]
        return 'Cardlist Updated!'

    def make_card_dictionaries(self, cardlist):
        '''
        Makes dictionaries of cards, keyed by card-id. First is with all card-info, second is
        with only cardnames as values
        '''
        carddict = {}
        namedict = {}
        for item in cardlist:
            cardid = item.pop('code')
            carddict[cardid] = item
            namedict[cardid] = item['title'].lower()
        return carddict, namedict
    

    def print_message(self, message):
        print(message)
        if self.logger is not None:
            self.logger.info(message)

    def newSearch(self, query):
        self.lastQuery = query
        self.lastQueryCounter = 0

    def isImage(self, boolean):
        self.lastQueryImage=boolean

    def execute_system(self, texttouple, message):
        text, vals = texttouple
        vals = vals.split()
        
        textDict = {
                'timing': 'https://i.imgur.com/dwYTrfF.jpg',
                'runtiming': 'https://i.imgur.com/dwYTrfF.jpg',
                'turntiming': 'https://i.imgur.com/phgyb33.jpg',
                'eirik': ':triumph:',
                'nikolai': CUSTOMEMOJI['[gianthead]'],
                'ulrik': 'I think you mean [[corroder]].',
                'christian': ':milk: :poop:',
                'vanadis': 'https://i.imgur.com/MJz4dAJ.jpg',
                'core': 'He warned us! Praise be the prophet!',
                'BOOM': 'http://i.imgur.com/XTslY6N.png',
                'beanstalk': 'http://i.imgur.com/S4EHlou.jpg'
                }

        functionDict = {
                'test': self.test,
                'psi': self.psi_game,
                'image': self.image_search,
                'gif': self.animate_search,
                'rip': self.rip,
                'saved': self.saved,
                'jvspls': self.sosorry,
                'jeevespls': self.sosorry,
                'jvsplease': self.sosorry,
                'jeevesplease': self.sosorry,
                'drils': self.drillstweets,
                'drills': self.drillstweets,
                'echo': self.echo_text,
                'update': self.NRDBGet,
                'random': self.randomNum,
                'report': self.reportMatch,
                'confirm': self.confirmMatch,
                'unconfirmed': self.unconfirmedMatches,
                'standings': self.leagueStandings,
                'decline': self.declineMatch,
                'league': self.leagueUsage,
                'mystanding': self.myStanding,
                'confirmall': self.confirmAllMatches,
                'declineall': self.declineAllMatches,
                'sts': self.stssearch,
                'stsupdate': self.STSGet
                }


        if text in textDict:
            return textDict[text]

        elif text in functionDict:
            return functionDict[text]((vals, message))

        elif text == 'lazarus':
            sys.exit(0)

        else:
            return None
    
    def test(self, data):
        message = data[1]
        return "I am posting in channel: "+message.channel.name+" with id "+message.channel.id


    def inLeagueChannel(self, message):
        return message.channel.name == "ligarapporter"


    def leagueUsage(self, data):
        if not self.inLeagueChannel(data[1]):
            return None
        leaguedescription = ("Jeeves tracks matches and ELO for Netrunner Norway discord tournaments. "
                "Commands only work in this channel, #ligarapporter.")
        joinusage = ("You are automatically added to the tournament if you report a match, or someone"
                " reports a match with you as an opponent. You don't have to lift a finger!")
        reportusage = ("To report a match, write \"!report @opponent win/loss\", where win/loss is "
                "whether you won/lost. The @opponent has to be a mention (include identifier).")
        confirmusage = ("To confirm a match, write \"!confirm matchID\", where matchID can "
                "be found by checking !unconfirmed. To decline a match, write "
                "\"!decline matchID\" instead. You can also confirm or decline all matches with "
                "\"!confirmall\" or \"!declineall\"")
        standingsusage = ("To check standings, write \"!standings\". ELO is recalculated every time "
                "a match is reported, and recalculated if someone declines a report. You can also check "
                "your own ELO rating with \"!mystanding\"")
        embed = discord.Embed(title="**JeevesBot League usage**", description = leaguedescription)
        embed.add_field(name="**Joining**", value=joinusage)
        embed.add_field(name="**Reporting**", value=reportusage)
        embed.add_field(name="**Confirming/Declining**", value=confirmusage)
        embed.add_field(name="**Standings**", value= standingsusage)
        return embed


    def reportMatch(self, data):
        vals = data[0]
        message = data[1]
        if not self.inLeagueChannel(message):
            return None
        if len(vals) < 2 or vals[1] not in ['win', 'loss'] or len(message.mentions) == 0:
            return "Usage: !report @opponent win/loss, where win/loss is whether you won/lost."
        won = False
        if message.author == message.mentions[0]:
            return "Stop hitting yourself!"
        if vals[1] == 'win':
            won = True
        matchID = self.league.add_unconfirmed(message.author, message.mentions[0], won)
        self.saveLeague()
        return "Added {author} {res} vs. {opp}.\n {opp} must confirm with !confirm {matchID}".format(
                author=message.author, opp=message.mentions[0], matchID=matchID, res=vals[1])

    def confirmMatch(self, data):
        vals = data[0]
        message = data[1]
        if not self.inLeagueChannel(message):
            return None
        if len(vals) == 0 or not vals[0].isdigit():
            return "Usage: !confirm matchID. Use !unconfirmed to check unconfirmed matches."
        if self.league.confirm_match(int(vals[0]), message.author):
            self.saveLeague()
            return "Match confirmed!"
        else:
            return "Could not find matchID or you are not the correct opponent."

    def confirmAllMatches(self, data):
        vals = data[0]
        message = data[1]
        if not self.inLeagueChannel(message):
            return None
        m = self.league.confirm_all_matches(message.author)
        return "Confirmed {} matches!".format(m)

    def declineMatch(self, data):
        vals = data[0]
        message = data[1]
        if not self.inLeagueChannel(message):
            return None
        if len(vals) == 0 or not vals[0].isdigit():
            return "Usage: !decline matchID. Use !unconfirmed to check unconfirmed matches."
        if self.league.decline_match(int(vals[0]), message.author):
            self.saveLeague()
            return "Match declined!"
        else: 
            return "Could not find matchID or you are not the correct opponent."

    def declineAllMatches(self, data):
        vals = data[0]
        message = data[1]
        if not self.inLeagueChannel(message):
            return None
        m = self.league.decline_all_matches(message.author)
        return "Declined {} matches!".format(m)

    def unconfirmedMatches(self, data):
        if not self.inLeagueChannel(data[1]):
            return None
        return self.league.return_unconfirmed()

    def leagueStandings(self, data):
        if not self.inLeagueChannel(data[1]):
            return None
        return self.league.show_standings()

    def myStanding(self, data):
        message = data[1]
        if not self.inLeagueChannel(message):
            return None
        return "Your ELO rating is: "+str(self.league.single_standing(message.author))

    def saveLeague(self):
        try:
            with open(self.leagueResults, 'wb') as leagueSave:
                pickle.dump(self.league, leagueSave, pickle.HIGHEST_PROTOCOL)
        except:
            self.print_message("Failed to save league :(")


    def stssearch(self, data):
        vals = data[0]
        if len(vals) == 0:
            return 'I love Slay the Spire as well!'
        if vals[0].lower() == 'enemy':
            searchdict = self.sts_enemy_names
            valdict = self.sts_enemies
        elif vals[0].lower() == 'relic':
            searchdict = self.sts_relic_names
            valdict = self.sts_relics
        elif vals[0].lower() == 'card':
            searchdict = self.sts_card_names
            valdict = self.sts_cards
        else:
            return "Usage: !sts enemy/relic/card name"
        best_match, certainty, best_key = process.extractOne(" ".join(vals[1:]), searchdict)
        return sts.sts_text(best_key, valdict)

    def echo_text(self, data):
        vals = data[0]
        if len(vals) > 0:
            return " ".join(vals)
        else:
            return None

    def randomNum(self, data):
        vals = data[0]
        if len(vals) > 0 and vals[0].isdigit() and int(vals[0]) > 0:
            return "Rolling 1d"+str(vals[0])+". You rolled: "+str(random.randint(1, int(vals[0])))
        else:
            return str(random.randint(1, 6))

    def psi_game(self, data):
        vals = data[0]
        if len(vals) > 0 and vals[0].isdigit() and int(vals[0]) >= 0 and int(vals[0]) < 3:
            g = random.randint(0,2)
            if int(vals[0]) == g:
                winmsg = ". You win!"
            else:
                winmsg = ". I win!"
            return "You bid: "+vals[0]+". I bid: "+str(g)+winmsg
        elif len(vals) > 0 and vals[0].isdigit():
            return "Bidding " + vals[0] + " is an illegal bid! DQ!"
        elif len(vals) > 0:
            return "That's not even a number!"
        else:
            return "Protip: Actually bidding helps your chances."

    def rip(self, data):
        vals = data[0]
        if len(vals) > 0:
            searchterm = " ".join(vals).lower().strip()
            cname, certainty = process.extract(searchterm, RIP, limit=1)[0]
        else:
            cname = RIP[random.randint(0,len(RIP)-1)]
        return ":skull_crossbones: "+cname + " is gone! Forever! :skull_crossbones:"

    def saved(self, data):
        vals = data[0]
        if len(vals) > 0:
            searchterm = " ".join(vals).lower().strip()
            cname, certainty = process.extract(searchterm, SAVED, limit=1)[0]
        else:
            cname = SAVED[random.randint(0,len(SAVED)-1)]
        return cname + " has been saved from the terrible beast of rotation! Praise Damon!"

    def drillstweets(self, data):
        all_tweets = self.twitterAPI.user_timeline(screen_name="drilrunner",count=200)
        while len(all_tweets) > 0:
            r = random.randrange(0, len(all_tweets)-1)
            tweet = all_tweets[r]
            if 'media' in tweet.entities:
                return tweet.entities['media'][0]['media_url']
            all_tweets.pop(r)

    def sosorry(self, data):
        if self.lastQuery is not None:
            msg1 = "I'm so sorry, of course I meant\n"
            self.lastQueryCounter += 1
            card_index, matchness = self.find_match()
            if self.lastQueryImage:
                msg2 = self.card_image_string(card_index)
            else:
                msg2 = self.card_info_string(card_index)
            return [msg1, msg2]
        else:
            return None

    def image_search(self, data):
        vals = data[0]
        if len(vals) > 0:
            query = "+".join(vals)
            self.print_message("Image search: "+query)
            result = self.googleSearcher.list(
                    q=query,
                    cx=GOOGLE_SEARCH_CX,
                    safe='high',
                    num=1,
                    searchType='image',
                    ).execute()
            if int(result['searchInformation']['totalResults']) > 0:
                self.print_message("Found image.")
                if query.find("slowpoke") > -1:
                    time.sleep(10)
                return result['items'][0]['link']
            else:
                self.print_message("Did not find image.")
                return "No image found :("
        else:
            return "Usage: !image query"

    def animate_search(self, data):
        vals = data[0]
        if len(vals) > 0:
            query = "+".join(vals)
            self.print_message("Image search: "+query)
            result = self.googleSearcher.list(
                q=query,
                cx=GOOGLE_SEARCH_CX,
                safe='high',
                num=1,
                searchType='image',
                fileType='gif',
                hq='animated',
                ).execute()
            if int(result['searchInformation']['totalResults']) > 0:
                self.print_message("Found animation.")
                if query.find("slowpoke") > -1:
                    time.sleep(10)
                return result['items'][0]['link']
            else:
                self.print_message("Did not find animation.")
                return "No animation found :("
        else:
            return "Usage: !gif query"


    def find_match(self):
        """
        Returns index of card matching query in the card name list.
        Also returns True if 'exact' match was found, or False if fuzzy matching was performed.
        """
        query = self.lastQuery.lower().strip()
        lQQ = self.lastQueryCounter
        self.print_message("Query: " + query)
        if query in ABBREVIATIONS:
            self.print_message("Applying abbrev.")
            query = ABBREVIATIONS[query].lower()

        if query in self.card_names.values():
            self.print_message("Matching from exact match.")
            return list(self.card_names.keys())[list(self.card_names.values()).index(query)], 100
        else:
            self.print_message("Fuzzy matching, finding match no: "+str(lQQ))
            best_match, certainty, best_key = process.extract(query, self.card_names, 
                    scorer= self.WSRatio, limit=(lQQ+1))[lQQ]
            return best_key, certainty

    
    def card_image_string(self, code):
        card_info = self.card_data[code]
        if "image_url" in card_info:
            return card_info["image_url"]
        else:
            return self.NRDB_URL_TEMPLATE.format(code=code)

    
    def card_info_string(self, code):
        """
        Returns nicely formatted card info to send to chat.
        Now in form of an embed!
        """
        card_info = self.card_data[code]
        if "text" not in card_info:
            card_info["text"] = ""
            self.print_message("blank", LOG_FILE)
        
        card_info["text"] = self.clean_text(card_info["text"])
        name = card_info["title"]
        
        if card_info["uniqueness"]:
            name = "◇ " + name

        if card_info["title"] in RIP:
            name = ":skull_crossbones: "+name

        if "flavor" in card_info:
            flavortext = self.clean_text("\n\n*{flavor}*".format(flavor=card_info["flavor"]))
        else:
            flavortext = ""

        if "keywords" in card_info:
            typeline = ("{type_code}: {keywords}").format(**card_info).title()
        else:
            typeline = ("{type_code}").format(**card_info).title()

        try:
            infcost = int(card_info["faction_cost"])
            #card might have a weird inf cost or inf cost is not a number
        except (KeyError, ValueError, TypeError): 
            infcost = 0

        infline = FACTIONS[card_info["faction_code"]]+" " + "●"*infcost

        if card_info["type_code"] == "agenda":
            statline = (
                "Advancement requirement: {advancement_cost}, "+CUSTOMEMOJI["[agenda]"]+": {agenda_points}"
                ).format(**card_info)
        else:
            statline = ""
            if "cost" in card_info:
                statline += "Cost: {cost} ".format(**card_info)
            if "strength" in card_info:
                statline += "Strength: {strength} ".format(**card_info)
            if "trash_cost" in card_info:
                statline += "Trash: {trash_cost} ".format(**card_info)
            if "memory_cost" in card_info:
                statline += "Memory: {memory_cost} ".format(**card_info)

        packd = next(filter(lambda pack: pack["code"] == card_info["pack_code"], self.pack_data))
        cycled = next(filter(lambda cycle: cycle["code"] == packd["cycle_code"], self.cycle_data))
        packline = packd["name"] + " - " + cycled["name"] + " #"+str(card_info["position"])
        card_decription = ""

        if card_info["type_code"] == "identity": # card is an ID
            try:
                linkinfo = ", {numlink} {linkemoji}".format(linkemoji=CUSTOMEMOJI["[link]"],
                        numlink=card_info["base_link"])
            except:
                linkinfo = ""
        
            card_description = (
                "*{infline} {minimum_deck_size}/{influence_limit}{linkinfo}*\n\n"
                "{text}{flavortext}"
                ).format(infline=infline, linkinfo=linkinfo, 
                    flavortext=flavortext, **card_info)
        
        else: # card is a "normal" card
            cardtext = card_info["text"] 
            
            card_description = (
                "*{typeline}*, {infline}\n{statline}\n"
                "{cardtext}{flavortext}"
                ).format(typeline=typeline, infline=infline,
                    statline=statline, cardtext=cardtext, flavortext=flavortext)
        cardurl = "https://netrunnerdb.com/en/card/"+str(code)
        cardEmbed = discord.Embed(title="**"+name+"**", url=cardurl,
                description=card_description)
        cardEmbed.set_footer(text=packline)
        cardEmbed.set_thumbnail(url=self.card_image_string(code))
        return cardEmbed

    
        
    def clean_text(self, text):
        strong_tag_regex = r"</?strong>" # matches <strong> and </strong>
        errata_tag_regex = r"</?errata>" # matches <errata> and </errata>
        trace_regex = r"<trace>Trace (.+?)</trace>" # matches <trace>Trace *</trace>

        text = re.sub(strong_tag_regex, "**", text)
        text = re.sub(errata_tag_regex, "*", text)

        def tracify(match):
            s = "Trace"
            num = match.group(1)
            for digit in num:
                s += SUPERSCRIPTS[digit]
            return s + ":"

        text = re.sub(trace_regex, tracify, text)
        for symbol in CUSTOMEMOJI:
            text = text.replace(symbol, CUSTOMEMOJI[symbol])

        for symbol in FACTIONS:
            text = text.replace('['+symbol+']', FACTIONS[symbol])

        return text


    def WSRatio(self, s1, s2, force_ascii=True, full_process=True):
        """
        Mostly copies Weighted ratio of FuzzyWuzzy, but changes it slightly for our purposese
        Does not punish large differences in size between strings, and incentivizes earlier hits
        """

        if full_process:
            p1 = utils.full_process(s1, force_ascii=force_ascii)
            p2 = utils.full_process(s2, force_ascii=force_ascii)
        else:
            p1 = s1
            p2 = s2

        if not utils.validate_string(p1):
            return 0
        if not utils.validate_string(p2):
            return 0

        try_partial = True
        unbase_scale = .95
        partial_scale = .90

        base = fuzz.ratio(p1, p2)
        len_ratio = float(max(len(p1),len(p2)))/min(len(p1),len(p2))

        # if strings are similar length, don't look at partials
        if len_ratio < 1.5:
            try_partial = False


        if try_partial:
            partial = fuzz.partial_ratio(p1, p2)*partial_scale
            ptsor = fuzz.partial_token_sort_ratio(p1, p2, full_process=False) \
                    * unbase_scale * partial_scale
            ptser = fuzz.partial_token_set_ratio(p1, p2, full_process=False) \
                    *unbase_scale * partial_scale

            return utils.intr(max(base, partial, ptsor, ptser)) - self.firstHit(p1, p2)
        else:
            tsor = fuzz.token_sort_ratio(p1, p2, full_process=False) * unbase_scale
            tser = fuzz.token_set_ratio(p1, p2, full_process=False) * unbase_scale

            return utils.intr(max(base, tsor, tser))

    def firstHit(self, s1, s2):
        # Sequencematcher is called like a bajillion times throughout everything
        m = SequenceMatcher(None, s1, s2)
        blocks = m.get_matching_blocks()
        maxB = max(map(lambda b: b[2], blocks))
        longestBlocks = filter(lambda b: b[2]== maxB, blocks)
        return min(map(lambda b: b[1], longestBlocks))

