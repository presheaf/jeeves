#!/usr/bin/python
# -*- coding: utf-8 -*-

import json, re, requests, random, time, tweepy, logging
from googleapiclient.discovery import build
from fuzzywuzzy import process, fuzz

from twitter_secrets import CONSUMER_KEY, CONSUMER_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET
from secrets import GOOGLE_API_KEY, GOOGLE_SEARCH_CX
from ripsave import RIP, SAVED
from customemoji import CUSTOMEMOJI, FACTIONS
from abbreviations import ABBREVIATIONS, SUPERSCRIPTS, PACKARRAY, PACKARRAY2

class JeevesBot:

	lastQuery = None
	lastQueryCounter = 0
	lastQueryImage = False

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
		self.NRDBGet()

	def NRDBGet(self):
		nrdburl = "https://netrunnerdb.com/api/2.0/public/"
		cardurl = nrdburl+"cards"
		packurl = nrdburl+"packs"
		cycleurl = nrdburl+"cycles"

		nrdb_card_api = requests.get(cardurl).json()
		nrdb_pack_api = requests.get(packurl).json()
		nrdb_cycle_api = requests.get(cycleurl).json()
		
		self.card_data = nrdb_card_api["data"]
		self.pack_data = nrdb_pack_api["data"]
		self.cycle_data = nrdb_cycle_api["data"]
		self.card_names = list(map(lambda card_dict: card_dict["title"].lower(), self.card_data))
		self.NRDB_URL_TEMPLATE = nrdb_card_api["imageUrlTemplate"]
		self.CGDB_URL_TEMPLATE = "http://www.cardgamedb.com/forums/uploads/an/med_ADN{packcode}_{cardcode}.png"

	

	def print_message(self, message):
		print(message)
		if self.logger is not None:
			self.logger.info(message)

	def newSearch(self, query):
		self.lastQuery = query
		self.lastQueryCounter = 0

	def isImage(self, boolean):
		self.lastQueryImage=boolean

	def execute_system(self, texttouple):
		text, vals = texttouple
		vals = vals.split()
		if text == 'psi':
			return self.psi_game(vals)
		elif text == 'image':
			return self.image_search(vals)
		elif text == 'gif':
			return self.animate_search(vals)
		elif text == 'update':
			self.print_message('Updating NRDB API')
			self.NRDBGet()
			return 'Cardlist updated!'
		elif text == 'eirik':
			return ':triumph:'
		elif text == 'ulrik':
			return 'I think you mean [[corroder]].'
		elif text == 'christian':
			return ':milk: :poop:'
		elif text == 'nikolai':
			return CUSTOMEMOJI['[gianthead]']
		elif text == 'vanadis':
			return 'https://i.imgur.com/MJz4dAJ.jpg'
		elif text == 'core':
			return 'He warned us! Praise be the prophet!'
		elif text == 'timing' or text == 'runtiming':
			return 'http://i.imgur.com/dwYTrfF.jpg'
		elif text == 'turntiming':
			return 'http://i.imgur.com/phgyb33.jpg'
		elif text == 'BOOM':
			return 'http://i.imgur.com/XTslY6N.png'
		elif text == 'echo':
			return self.echo_text(vals)
		elif text == 'saved':
			return self.saved(vals)
		elif text == 'rip':
			return self.rip(vals)
		elif text == 'jvspls':
			return self.sosorry()
		elif text == 'drills':
			return self.drillstweets()
		elif text == 'lazarus':
			sys.exit(0)
		else:
			return None


	def echo_text(self, vals):
		if len(vals) > 0:
			return " ".join(vals)
		else:
			return None

	def psi_game(self, vals):
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

	def rip(self, vals):
		if len(vals) > 0:
			searchterm = " ".join(vals).lower().strip()
			cname, certainty = process.extract(searchterm, RIP, limit=1)[0]
		else:
			cname = RIP[random.randint(0,len(RIP)-1)]
		return ":skull_crossbones: "+cname + " is gone! Forever! :skull_crossbones:"

	def saved(self, vals):
		if len(vals) > 0:
			searchterm = " ".join(vals).lower().strip()
			cname, certainty = process.extract(searchterm, SAVED, limit=1)[0]
		else:
			cname = SAVED[random.randint(0,len(SAVED)-1)]
		return cname + " has been saved from the terrible beast of rotation! Praise Damon!"

	def drillstweets(self):
		all_tweets = self.twitterAPI.user_timeline(screen_name="drilrunner",count=200)
		while len(all_tweets) > 0:
			r = random.randrange(0, len(all_tweets)-1)
			tweet = all_tweets[r]
			if 'media' in tweet.entities:
				return tweet.entities['media'][0]['media_url']
			all_tweets.pop(r)

	def sosorry(self):
		if self.lastQuery is not None:
			msg = "I'm so sorry, of course I meant\n"
			self.lastQueryCounter += 1
			card_index, matchness = self.find_match()
			if self.lastQueryImage:
				msg += self.card_image_string(card_index)
			else:
				msg += self.card_info_string(card_index)
			return msg
		else:
			return None

	def image_search(self, vals):
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

	def animate_search(self, vals):
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

		if query in self.card_names:
			self.print_message("Matching from exact match.")
			return self.card_names.index(query), 100
		else:
			self.print_message("Fuzzy matching, finding match no: "+str(lQQ))
			best_match, certainty = process.extract(query, self.card_names, 
					limit=(lQQ+1))[lQQ]
			return self.card_names.index(best_match), certainty

	
	def card_image_string(self, index):
		card_info = self.card_data[index]
		packd = next(filter(lambda pack: pack["code"] == card_info["pack_code"], self.pack_data))
		cycled = next(filter(lambda cycle: cycle["code"] == packd["cycle_code"], self.cycle_data))
		if (cycled["position"] < 6) or (cycled["position"]==6 and packd["position"]==1):
			return self.NRDB_URL_TEMPLATE.format(code=card_info["code"])
		else:
			if cycled["position"] < 20:
				packcode = PACKARRAY[cycled["position"]-6]+packd["position"]
			else:
				packcode = PACKARRAY2[cycled["position"]-20]+packd["position"]
			cardcode = card_info["position"]
			return self.CGDB_URL_TEMPLATE.format(packcode=packcode, cardcode=cardcode)

	
	def card_info_string(self, index):
		"""
		Returns nicely formatted card info to send to chat.
		"""
		card_info = self.card_data[index]
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
		packline = "\n\n*" + packd["name"] + " - " + cycled["name"] + "* #"+str(card_info["position"])


		if card_info["type_code"] == "identity": # card is an ID
			try:
				linkinfo = ", {numlink} {linkemoji}".format(linkemoji=CUSTOMEMOJI["[link]"],
						numlink=card_info["base_link"])
			except:
				linkinfo = ""
		
			return (
				"**{name}**\n"
				"*{infline} {minimum_deck_size}/{influence_limit}{linkinfo}*\n\n"
				"{text}{flavortext}{packline}"
				).format(name=name, infline=infline, linkinfo=linkinfo, 
					flavortext=flavortext, packline=packline, **card_info)
		
		else: # card is a "normal" card
			cardtext = card_info["text"] 
			
			return (
				"**{name}**\n*{typeline}*, {infline}\n{statline}\n"
				"{cardtext}{flavortext}{packline}"
				).format(name=name, typeline=typeline, infline=infline,
					statline=statline, cardtext=cardtext, flavortext=flavortext, 
					packline=packline)

	
		
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


