#!/usr/bin/python
# -*- coding: utf-8 -*-

import discord, re, subprocess, importlib

import pickle

from secrets import JEEVES_KEY

from jeeves_bot import JeevesBot


##### NRDB lookup bot.
##### Responds to [[cardnames]] with a message with info. And a bunch of other things

##### TODO: make card formatting nicer

client = discord.Client()

# logfile
LOG_FILE = "jeeveslog.log"

# Start up JeevesBot
jeeves = JeevesBot(LOG_FILE)

def restart():
    """
    Pulls newest version of jeevesbot and reloads jeevesbot
    """
    subprocess.call(["git", "fetch"])
    subprocess.call(["git", "checkout jeeves_bot.py"])
    importlib.reload(JeevesBot)
    jeeves = JeevesBot(LOG_FILE)
    return "Bot Updated!"

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

@client.event
async def on_message(message):
    # we do not want the bot to reply to itself
    if message.author == client.user:
        return
    
    queries = extract_queries(message.content)

    for query, query_type in queries:
        if query_type != "system":
            jeeves.newSearch(query)
            card_index, matchness = jeeves.find_match()
            if query_type == "card":
                jeeves.isImage(False)
                msg = jeeves.card_info_string(card_index)
            else:
                jeeves.isImage(True)
                msg = jeeves.card_image_string(card_index)
        elif query_type == "system":
            if message.content.startswith('!echo'):
                jeeves.print_message("Forced to say: " + message.content[6:]+"\n by: " + message.author.name)
                await client.delete_message(message)
            msg = jeeves.execute_system(query, message)
        if msg is not None:
            if type(msg) is not list:
                msg = [msg]
            for m in msg:
                if type(m) is str:
                    await client.send_message(message.channel, m)
                else:
                    await client.send_message(message.channel, embed=m)


@client.event
async def on_ready():
    jeeves.print_message('Logged in as')
    jeeves.print_message(client.user.name)
    jeeves.print_message('------')


if __name__ == "__main__":
    client.run(JEEVES_KEY)

