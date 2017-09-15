# -*- coding: utf-8 -*-

import discord, json, re, requests, subprocess, sys, random, time
from fuzzywuzzy import process
from googleapiclient.discovery import build


from secrets import JEEVES_KEY, GOOGLE_API_KEY, GOOGLE_SEARCH_CX
from abbreviations import ABBREVIATIONS, SUPERSCRIPTS
from customemoji import CUSTOMEMOJI, FACTIONS
from ripsave import RIP, SAVED

##### NRDB lookup bot.
##### Responds to [[cardnames]] with a message with info.

##### TODO: make card formatting nicer
##### TODO: add support for requesting images

client = discord.Client()

url = "https://netrunnerdb.com/api/2.0/public/cards"
nrdb_api = requests.get(url).json()
card_data = nrdb_api["data"]
IMAGE_URL_TEMPLATE = nrdb_api["imageUrlTemplate"]

card_names = list(map(lambda card_dict: card_dict["title"].lower(),
                      card_data))

googleSearcher = build("customsearch", "v1", developerKey=GOOGLE_API_KEY).cse()

LOG_FILE = "jeeveslog.log"


def print_message(message):
    print(message)
    with open(LOG_FILE, "a+") as f:
        f.write(message)
        f.write("\n")


def restart():
    """Call restart script and exit. 
    Not clean but hopefully functional."""
    print_message("Restarting")
    subprocess.Popen(["bash", "start.sh"])
    sys.exit(0)

def extract_queries(msg_text):
    """
    Returns list of queries from a Discord message
    """
    card_query_regex = r"\[\[(.+?)\]\]" # matches [[cardnames]]
    image_query_regex = r"\{\{(.+?)\}\}" # matches {{cardnames}}
    system_query_regex = r"^\!(\S+)(.*)" # matches !input options

    return (
        [(match.group(1), "card")
         for match in re.finditer(card_query_regex, msg_text)] +
        [(match.group(1), "image")
         for match in re.finditer(image_query_regex, msg_text)] +
        [((match.group(1), match.group(2)), "system")
         for match in re.finditer(system_query_regex, msg_text)]
    )

def find_match(query):
    """
    Returns index of card matching query in the card name list.
    Also returns True if 'exact' match was found, or False if fuzzy matching was performed.
    """
    query = query.lower().strip()
    print_message("Query: " + query)
    if query in ABBREVIATIONS:
        print_message("Applying abbrev.")
        query = ABBREVIATIONS[query].lower()
        
    if query in card_names:
        print_message("Matching from exact match.")
        return card_names.index(query), 100
    else:
        print_message("Fuzzy matching.")
        best_match, certainty = process.extract(query, card_names, limit=1)[0]
        return card_names.index(best_match), certainty


def card_image_string(index):
    return IMAGE_URL_TEMPLATE.format(code=card_data[index]["code"])


def card_info_string(index):
    """
    Returns nicely formatted card info to send to chat.
    """
    
    card_info = card_data[index]
    if "text" not in card_info:
        card_info["text"] = ""
        print_message("blank")
    card_info["text"] = clean_text(card_info["text"])
    name = card_info["title"]

    if name in RIP:
        name = name+":skull_crossbones:"
    if card_info["uniqueness"]:
        name = "◇ " + name


    if "flavor" in card_info:
        flavortext = "\n\n*{flavor}*".format(flavor=card_info["flavor"])
    else:
        flavortext = ""

    
    if "keywords" in card_info:
        typeline = (
            "{type_code}: {keywords}"
        ).format(**card_info).title()
    else:
        typeline = (
            "{type_code}"
        ).format(**card_info).title()

        
    try:
        infcost = int(card_info["faction_cost"])
    except (KeyError, ValueError): #card has no inf cost or inf cost is not a number
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


            
    if card_info["type_code"] == "identity": # card is an ID
        try:
            linkinfo = ", {numlink} {linkemoji}".format(linkemoji=CUSTOMEMOJI["[link]"],
                                                        numlink=card_info["base_link"])
        except:
            linkinfo = ""
        return (
            "**{title}**\n"
            "*{infline} {minimum_deck_size}/{influence_limit}{linkinfo}*\n\n"
            "{text}{flavortext}"
        ).format(infline=infline, linkinfo=linkinfo, 
                 flavortext=flavortext, **card_info)
    else: # card is a "normal" card
        cardtext = card_info["text"] 
        
        

        return (
            "**{name}**\n*{typeline}*, {infline}\n{statline}\n"
            "{cardtext}{flavortext}"
        ).format(name=name, typeline=typeline, infline=infline,
                 statline=statline, cardtext=cardtext, flavortext=flavortext)
        

def clean_text(text):
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
  
def execute_system(texttouple):
    text, vals = texttouple
    vals = vals.split()
    if text == 'psi':
        return psi_game(vals)
    elif text == 'image':
        return image_search(vals)
    elif text == 'gif':
        return animate_search(vals)
    elif text == 'update':
        restart()
    elif text == 'eirik':
        return ':triumph:'
    elif text == 'ulrik':
        return 'I think you mean [[corroder]].'
    elif text == 'christian':
        return ':milk: :poop:'
    elif text == 'nikolai':
        return CUSTOMEMOJI['[hayley]']
    elif text == 'core':
        return 'Core 2.0 Confirmed'
    elif text == 'timing':
        return 'http://i.imgur.com/2vCRAl5.jpg'
    elif text == 'turntiming':
        return 'http://i.imgur.com/bnSC0Nv.jpg'
    elif text == 'BOOM':
        return 'http://i.imgur.com/XTslY6N.png'
    elif text == 'echo':
        return echo_text(texttouple)
    elif text == 'saved':
        return saved()
    elif text == 'rip':
        return rip()
    elif text == 'lazarus':
        sys.exit(0)
    else:
        return None


def echo_text(texttouple):
    text, vals = texttouple
    if len(vals) > 0:
        print_message("Forced to say: "+vals)
        return vals
    else:
        return None
    
def psi_game(vals):
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

def rip():
    cname = RIP[random.randint(0,len(RIP)-1)]
    return ":skull_crossbones: "+cname + " is gone! Forever! :skull_crossbones:"

def saved():
	cname = SAVED[random.randint(0,len(SAVED)-1)]
	return cname + " has been saved from the terrible beast of rotation! Praise Damon!"

def image_search(vals):
  if len(vals) > 0:
    query = "+".join(vals)
    print_message("Image search: "+query)
    result = googleSearcher.list(
		    q=query,
		    cx=GOOGLE_SEARCH_CX,
		    safe='high',
		    num=1,
		    searchType='image',
		    ).execute()
    if int(result['searchInformation']['totalResults']) > 0:
        print_message("Found image.")
        if query.find("slowpoke") > -1:
          time.sleep(10)
        return result['items'][0]['link']
    else:
        print_message("Did not find image.")
        return "No image found :("
  else:
    return "Usage: !image query"

def animate_search(vals):
  if len(vals) > 0:
    query = "+".join(vals)
    print_message("Image search: "+query)
    result = googleSearcher.list(
		    q=query,
		    cx=GOOGLE_SEARCH_CX,
		    safe='high',
		    num=1,
		    searchType='image',
		    fileType='gif',
		    hq='animated',
		    ).execute()
    if int(result['searchInformation']['totalResults']) > 0:
        print_message("Found animation.")
        if query.find("slowpoke") > -1:
          time.sleep(10)
        return result['items'][0]['link']
    else:
        print_message("Did not find animation.")
        return "No animation found :("
  else:
    return "Usage: !gif query"

@client.event
async def on_message(message):
    # we do not want the bot to reply to itself
    if message.author == client.user:
	    return

    queries = extract_queries(message.content)
    
    for query, query_type in queries:
        if query_type != "system":
          card_index, matchness = find_match(query)
          if query_type == "card":
            msg = card_info_string(card_index)
          else:
             msg = card_image_string(card_index)
        elif query_type == "system":
          msg = execute_system(query)
          if message.content.startswith('!echo'):
            print_message("Forced by: " + message.author.name)
            await client.delete_message(message)
        if msg is not None:
            await client.send_message(message.channel, msg)

            
@client.event
async def on_ready():
    print_message('Logged in as')
    print_message(client.user.name)
    print_message('------')


if __name__ == "__main__":    
    client.run(JEEVES_KEY)

