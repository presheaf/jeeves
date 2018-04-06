import json, requests, re, discord

siteused = "https://slaythespire.gamepedia.com/"
baseurl = siteused+"api.php"
baseparameters = {
        'action': 'query',
        'format': 'json',
        'formatversion': '2'
        }
contentparameters = {
        'prop':'revisions',
        'rvprop':'content'
        }
categoryparameters = {
        'generator':'categorymembers',
        'gcmlimit': '50',
        'gcmtype': 'page'
        }
stdparam = baseparameters.copy()
stdparam.update(contentparameters)
stdparam.update(categoryparameters)

def wikiquery(request):
    # Fetches data from the wiki as a generator
    lastContinue={}
    while True:
        #Clone original request
        req = request.copy()
        # Modify it with the values returned in the 'continue' section of the last result
        req.update(lastContinue)
        # Call API
        result = requests.get(baseurl, params=req).json()
        if 'error' in result:
            raise RuntimeError(result['error'])
        if 'warnings' in result:
            print(result['warnings'])
        if 'query' in result:
            yield result
        if 'continue' not in result:
            break
        lastContinue = result['continue']

def formatDict(item, info):
    content = item['revisions'][0]['content']
    name = item['title']
    reg = r"\{\{infobox "+info+r"([\s\S]*?)\}\}"
    match = re.search(reg, content, flags=re.IGNORECASE)
    if match is not None:
        firstM = match.group(1).split('|')
    else:
        firstM = []
    returnDict={}
    for vals in firstM:
        splitvals = vals.split('=')
        if len(splitvals) == 2:
            key = splitvals[0].strip()
            val = splitvals[1].strip()
            returnDict[key]=val
    returnDict['item'] = info
    returnDict['name'] = name
    returnDict['content'] = content
    return returnDict

def makeDictOfList(pagelist, pagedict, namedict, info=None):
    for item in pagelist:
        if item['title'].lower() == 'relics' or item['title'].lower() == 'enemies':
            continue
        pageid = item.pop('pageid')
        if ('revisions' in item and
                item['revisions'][0]['content'].find('{{delete}}') < 0):
            pagedict[pageid] = formatDict(item,info)
            namedict[pageid] = pagedict[pageid]['name']

            


def fetchCards():
    cardparameters = {
            'gcmtitle':'Category:Cards'
            }
    cardparameters.update(stdparam)
    carddict = {}
    cardnamedict = {}
    for q in wikiquery(cardparameters):
        makeDictOfList(q['query']['pages'], carddict, cardnamedict, 'card')
    return carddict, cardnamedict

def fetchEnemies():
    enemyparameters = {
            'gcmtitle':'Category:Enemies'
            }
    enemyparameters.update(stdparam)
    enemydict = {}
    enemynamedict={}
    for q in wikiquery(enemyparameters):
        makeDictOfList(q['query']['pages'], enemydict, enemynamedict, 'enemy')
    return enemydict, enemynamedict

def fetchRelics():
    relicparameters = {
            'gcmtitle': 'Category:Relics'
            }
    relicparameters.update(stdparam)
    relicdict = {}
    relicnamedict={}
    for q in wikiquery(relicparameters):
        makeDictOfList(q['query']['pages'], relicdict, relicnamedict, 'relic')
    return relicdict, relicnamedict

def sts_text(dictkey, dictUsed):
    element = dictUsed[dictkey].copy()
    name = element.pop('name')
    itemurl = siteused + "?curid="+str(dictkey)
    cardEmbed = discord.Embed(title="**"+name+"**",
            url=itemurl)
    if 'image' in element:
        ima = element.pop('image')
        imageurl = siteused+"Special:FilePath/"+ima
        cardEmbed.set_thumbnail(url=imageurl)
    # Ting vi ikke vil printe
    itemType = element.pop('item')
    content = element.pop('content')
    for key in element:
        fieldName = key.capitalize()
        fieldValue = element[key]
        fieldValue = fieldValue.replace(r"<br/>", "\n")
        cardEmbed.add_field(name=fieldName, value=fieldValue)

    cardEmbed.set_footer(text="Missing or wrong info? Update the wiki-page! That's how I learn!")
    return cardEmbed
