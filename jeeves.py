import discord, json, re
from fuzzywuzzy import process

from secrets import JEEVES_KEY
from abbreviations import ABBREVIATIONS


##### NRDB lookup bot.
##### Responds to [[cardnames]] with a message with info.

##### TODO: make card formatting nicer
##### TODO: make card name matching less strict
##### TODO: add support for requesting images

client = discord.Client()

ABBREVIATIONS = {
    "opus": "Magnum Opus",
    "mopus": "Magnum Opus",
    "temujin": "Temüjin Contract"
}

with open("cards.json") as f:
    nrdb_api = json.load(f)
    card_data = nrdb_api["data"]
    IMAGE_URL_TEMPLATE = nrdb_api["imageUrlTemplate"]

card_names = list(map(lambda card_dict: card_dict["title"].lower(),
                      card_data))


def extract_queries(msg_text):
    """
    Returns list of queries from a Discord message
    """
    #query_regex = r"\[\[(\w*?)\]\]" # matches [[cardnames]]
    query_regex = r"\[\[([\s_a-zA-Z0-9]*?)\]\]" # matches [[cardnames]]
    

    return [match.group(1)
            for match in re.finditer(query_regex, msg_text)]

def find_match(query):
    """
    Returns index of card matching query in the card name list.
    Also returns True if 'exact' match was found, or False if fuzzy matching was performed.
    """
    query = query.lower().strip()
    print(query)
    if query in ABBREVIATIONS:
        print("Matching from abbrev.")
        return card_names.index(ABBREVIATIONS[query].lower()), True
    elif query in card_names:
        print("Matching from exact match.")
        return card_names.index(query), True
    else:
        print("Fuzzy matching.")
        best_match = process.extract(query, card_names, limit=1)[0][0]
        return card_names.index(best_match), False

def card_info_string(index):
    """
    Returns nicely formatted card info to send to chat.
    """
    card_info = card_data[index]
    
    name = card_info["title"]
    if card_info["uniqueness"]:
        name = "* " + name
    
    if "keywords" in card_info:
        typeline = (
            "{type_code}: {keywords}"
        ).format(**card_info)
    else:
        typeline = (
            "{type_code}"
        ).format(**card_info)

        
    if "faction_cost" in card_info:
        infline = "{faction_code}, {faction_cost} inf".format(**card_info)
    else:
        infline = "{faction_code}".format(**card_info)

        
    if card_info["type_code"] == "agenda":
        statline = (
            "Advancement requirement: {advancement_cost}, agenda points: {agenda_points}"
        ).format(**card_info)
    else:
        statline = ""
        if "cost" in card_info:
            statline += "Cost: {cost} ".format(**card_info)
        if "strength" in card_info:
            statline += "Strength: {strength} ".format(**card_info)
        if "trash_cost" in card_info:
            statline += "Trash: {trash_cost} ".format(**card_info)

            
    if card_info["type_code"] == "identity": # card is an ID
        return (
            "**{title}**\n"
            "*{faction_code}, {minimum_deck_size}/{influence_limit}*\n\n"
            "{text}\n\n*{flavor}"
        ).format(**card_info)
    else: # card is a "normal" card
        cardtext = card_info["text"]
        if "flavor" in card_info:
            cardtext += "\n\n *{}*".format(card_info["flavor"])
        

        return (
            "**{name}**\n*{typeline}*\n{infline}\n{statline}\n"
            "{cardtext}"
        ).format(name=name, typeline=typeline, infline=infline,
                 statline=statline, cardtext=cardtext)
        


@client.event
async def on_message(message):
    # we do not want the bot to reply to itself
    if message.author == client.user:
        return
    
    queries = extract_queries(message.content)
    
    for query in queries:
        card_index, exact_match = find_match(query)
        if exact_match:
            msg = "Was *this* your card? \n\n"
        else:
            msg = "Not 100% sure, but was *this* your card? \n\n"

        msg = msg + card_info_string(card_index)
        print(msg)
        await client.send_message(message.channel, msg)

@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print('------')

client.run(JEEVES_KEY)
