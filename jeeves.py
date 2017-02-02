import discord, json, re, requests, subprocess, sys, random
from fuzzywuzzy import process

from secrets import JEEVES_KEY
from abbreviations import ABBREVIATIONS
from customemoji import CUSTOMEMOJI


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

SYSTEM_CALLS = ["update", "psi", "eirik", "ulrik"]

def restart():
    """Call restart script and exit. 
    Not clean but hopefully functional."""
    print("Restarting")
    subprocess.Popen(["bash", "start.sh"])
    sys.exit(0)

def extract_queries(msg_text):
    """
    Returns list of queries from a Discord message
    """
    card_query_regex = r"\[\[(.+?)\]\]" # matches [[cardnames]]
    image_query_regex = r"\{\{(.+?)\}\}" # matches {{cardnames}}
    # system_query_regex = r"^\!(\S+)" # matches !input

    if msg_text[0] == "!" and msg_text[1:] in SYSTEM_CALLS:
        system_calls = [(msg_text[1:], "system")]
    else:
        system_calls = []
    return (
        [(match.group(1), "card")
         for match in re.finditer(card_query_regex, msg_text)] +
        [(match.group(1), "image")
         for match in re.finditer(image_query_regex, msg_text)] +
        system_calls
    )

def find_match(query):
    """
    Returns index of card matching query in the card name list.
    Also returns True if 'exact' match was found, or False if fuzzy matching was performed.
    """
    query = query.lower().strip()
    print("Query: " + query)
    if query in ABBREVIATIONS:
        print("Applying abbrev.")
        query = ABBREVIATIONS[query].lower()
        
    if query in card_names:
        print("Matching from exact match.")
        return card_names.index(query), 100
    else:
        print("Fuzzy matching.")
        best_match, certainty = process.extract(query, card_names, limit=1)[0]
        return card_names.index(best_match), certainty


def card_image_string(index):
    return IMAGE_URL_TEMPLATE.format(code=card_data[index]["code"])


def card_info_string(index):
    """
    Returns nicely formatted card info to send to chat.
    """
    card_info = card_data[index]
    card_info["text"] = clean_text(card_info["text"])
    name = card_info["title"]
    if card_info["uniqueness"]:
        name = ":eight_pointed_black_star: " + name
    
    if "keywords" in card_info:
        typeline = (
            "{type_code}: {keywords}"
        ).format(**card_info).title()
    else:
        typeline = (
            "{type_code}"
        ).format(**card_info).title()

        
    if "faction_cost" in card_info:
        infline = "{faction_code}, {faction_cost} inf".format(**card_info).title()
    else:
        infline = "{faction_code}".format(**card_info).title()

        
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
            "*{infline}, {minimum_deck_size}/{influence_limit}*\n\n"
            "{text}\n\n*{flavor}*"
        ).format(infline=infline, **card_info)
    else: # card is a "normal" card
        cardtext = card_info["text"]
        if "flavor" in card_info:
            cardtext += "\n\n *{}*".format(card_info["flavor"])
        

        return (
            "**{name}**\n*{typeline}*\n{infline}\n{statline}\n"
            "{cardtext}"
        ).format(name=name, typeline=typeline, infline=infline,
                 statline=statline, cardtext=cardtext)
        

def clean_text(text):
    strong_tag_regex = r"</?strong>" # matches <strong> and </strong>

    text = re.sub(strong_tag_regex, "**", text)
    for symbol in CUSTOMEMOJI:
        text = text.replace(symbol, CUSTOMEMOJI[symbol])
        
    
    
    
    return text
  
def execute_system(text):
    if text == 'psi':
      return 'I bid ' + str(random.randint(0,2))
    if text == 'update':
      restart()
    if text == 'eirik':
      return ':triumph:'
    if text == 'ulrik':
      return 'I think you mean [[corroder]].'


@client.event
async def on_message(message):
    # we do not want the bot to reply to itself
    if message.author == client.user:
        return
    
    queries = extract_queries(message.content)
    
    for query, query_type in queries:
        if query_type != "system":
          card_index, matchness = find_match(query)
          if matchness == 100:
            msg = "Was *this* your card? \n\n"
          else:
            msg = "I am {}% sure that *this* was your card: \n\n".format(matchness)
          if query_type == "card":
            msg = msg + card_info_string(card_index)
          else:
             msg = msg + card_image_string(card_index)
        elif query_type == "system":
          msg = execute_system(query)
          #msg = "This is a system message. You wrote !{}".format(query)
        await client.send_message(message.channel, msg)

@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print('------')

if __name__ == "__main__":    
    client.run(JEEVES_KEY)

