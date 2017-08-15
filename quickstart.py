#TODO spread out functions into different files
from __future__ import print_function
import httplib2
import os
import re, string

from fuzzywuzzy import fuzz
from fuzzywuzzy import process

import discord
import aiohttp
import asyncio

from datetime import datetime
from datetime import timedelta

from apiclient import discovery
from oauth2client import client as Oclient
from oauth2client import tools
from oauth2client.file import Storage

import subprocess

try:
    import argparsew
    flags = argparse.ArgumentParser(parents=[tools.argparser]).parse_args()
except ImportError:
    flags = None

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/sheets.googleapis.com-python-quickstart.json
SCOPES = 'https://www.googleapis.com/auth/spreadsheets'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'RelayBot'
TRUSTED_IDS = ['278708481995833354','279810303170969620','271379542688399362','278723003146174465','233963211588632576','260836495236005888','232074884086366208']

client = discord.Client()
update_index = 0

SHEET_ENUM = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z', 'AA', 'AB',
              'AC', 'AD', 'AE', 'AF', 'AG', 'AH']
service = None

gym_channels_ = []
linking_ = False

gyms = {}
commands = {}
region_display = []
regions = {}
descriptions = {}

#basic async url fetch used for fetching discord message attachments
async def fetch(session, url):
    with async_timeout.timeout(10):
        async with session.get(url) as response:
            return await response.text()

#parses command to command dict
async def parse_command(message):
    if message.content.split()[0] in commands.keys():
        await commands[message.content.split()[0]](message)
    else:
        await client.send_message(message.channel, 'Critique: Invalid command.')

    
#for use on non-threadsafe operations that may take a great deal of time
async def dumb_wait(func=None, arg=None):
    for i in range(0,100):
       if waiting_:
           await asyncio.sleep(1)
       else:
           return i

async def find_gym(message):
    #ration = fuzz.ratio(message.content, "The Start of Something Big")
    tokens = message.content.split()
    printed = []
    subs = []
    if len(tokens) < 5:
        subs = [" ".join(tokens)]
    else:
        for i in range(0,len(tokens)-4):
            subs.append(" ".join(tokens[i:i+5]))
    choices = gyms.keys()
    for sub in subs:
        for key in choices:
            ration = fuzz.token_sort_ratio(sub, key)
            ration += fuzz.token_set_ratio(sub, key)

            if ration > 135 and key not in printed:
                print("%s: %s" % ("".join([s for s in key if s in string.printable]),ration))
                await client.send_message(message.channel, "%s: %s" % (key, gyms[key]['link']))
                printed.append(key)
            elif ration > 100:
                print("%s: %s" % ("".join([s for s in key if s in string.printable]),ration))
                
async def find_sector(message):
    args = message.content.split()
    
    if len(args) > 3:
        return #error
    elif len(args) == 3:
        reg = ("%s%s"%(args[1],args[2])).capitalize()
    else:
        reg = args[1].capitalize()
    if reg in regions:
        sect = regions[reg][0]
        await client.send_message(message.channel, "Sector %s: %s\n" % (sect['region'], descriptions[sect['region']]))
        for gym in regions[reg]:
            await client.send_message(message.channel, "%s: %s" % (gym['gym'], gym['link']))
    else:
        return #error
    
           
#handles messages
@client.event
async def on_message(message):
    global queue_, waiting_
    # we do not want the bot to reply to itself
    if message.author == client.user:
        return
    if message.content.startswith(';'):
        if message.content.startswith(';;;') and message.author.id in TRUSTED_IDS:
            await parse_command(message)
        elif message.channel.id in gym_channels_:
            await parse_command(message)
        return
    elif ';' in message.content and linking_ and message.channel.id in gym_channels_:
        foundGyms = await find_gym(message)
    
    '''if message.attachments and linking_ and message.channel.id in medal_channels_:
        await image_channel(message)
    elif message.channel.id in scan_channels_:
        await scan_channel(message)
    elif message.channel.id in udex_channels_:
        await udex_channel(message)
        return'''

#when bot comes online
@client.event
async def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')

#returns the current week starting on weekStart
def week_prefix(date=None):
    weekStart = 5 #saturday
    if date is None:
        d = datetime.today()
        d1 = datetime.today()
        d2 = datetime.today()
    else:
        d = date
        d1 = date
        d2 = date
    if d.weekday() < weekStart:
        offset = timedelta(0-(d.weekday() - weekStart + 7))
    else:
        offset = timedelta(0-(d.weekday() - weekStart))
    d1 = d1 + offset
    d2 = d2 + offset + timedelta(days=6)
    #attempted to make date both UNIX and Windows compatible for folder names
    return ("%s-%s-%s--%s-%s-%s" % (d1.month,d1.day,d1.year,d2.month,d2.day,d2.year))

#yeah
def isfloat(value):
  try:
    float(value)
    return True
  except ValueError:
    return False

#gets Google API credentials
def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or iSf the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'sheets.googleapis.com-python-quickstart.json')

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = Oclient.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else: # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials

#enables the bot to start collection images: must init to a channel first
async def start_linking(message):
    global linking_
    linking_ = True
    await client.send_message(message.channel, 'Relay now active.')

#disables image collection
async def stop_linking(message):
    global linking_
    linking_ = False
    await client.send_message(message.channel, 'Relay no longer active.')

#prints whether or not the bot is accepting images
async def status_check(message):
    if linking_:
        await client.send_message(message.channel, 'Relay is active.')
    else:
        await client.send_message(message.channel, 'Relay is not active.')
        
async def toggle_region_display(message):
    global region_display
    if message.channel.id in region_display:
        region_display.remove(message.channel.id)
        await client.send_message(message.channel, 'Hiding gym regional info.')
    else:
        region_display.append(message.channel.id)
        await client.send_message(message.channel, 'Displaying gym regional info.')

#right now it is not really custom
async def custom_message(message):
    await client.send_message(message.channel, 'Smug challenge: Bring it on, meatbag.')


#prints help message
async def print_help(message):
    await client.send_message(message.channel, '%s%s%s%s%s%s' % (';startlinking: starts linking information\n',
                                                                 ';stoplinking: stops linking information\n',
                                                                 ';status: whether or not image processing is active\n',
                                                                 ';help: this information'))

#initializes the bot to a specific discord channel
async def initialize_channel(message):
    global gym_channels_
    
    args = message.content.split()
    if len(args) < 2:
        await client.send_message(message.channel, 'Channel purpose required.')
        return
    
    if message.channel.id in gym_channels_:
        await client.send_message(message.channel, 'Channel already initialized.')    
    elif args[1] == 'gym' and message.channel.id not in gym_channels_:
        gym_channels_.append(message.channel.id)
        await client.send_message(message.channel, 'Initialized to channel %s.' % (message.channel.id))
    else:
        await client.send_message(message.channel, 'Channel purpose must be "gym"')

#updates local data lists from the reference sheet
def update_lists():
    global service, gyms, regions

    spreadsheetId = '1n88ieu34cejbSpiQOlK71B_8tpGjAAIzvw7Le3E7N8U'
    rangeName = "'Links'!A2:E"
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheetId, range=rangeName).execute()
    values = result.get('values', [])
    print('%s' % (result['range']))
    if not values:
        print("Error: no users found.")
        return
    else:
        for row in values:
            # generate user lookup index so don't have to query all the time
            #print('%s, %s' % (row[0], row[1]))
            if len(row) < 5:
                link = 'unknown'
                if len(row) < 4:
                    desc = 'unknown'
            else:
                desc = row[3]
                link = row[4]
            gyms[row[0]] = { 'gym' : row[0], 'link' : link, 'region' : row[1], 'number' : row[2], 'description' : desc }
            
            if row[1] not in regions.keys():
                regions[row[1]] = [ { 'gym' : row[0], 'link' : link, 'region' : row[1], 'number' : row[2], 'description' : desc } ]
            else:
                regions[row[1]].append( { 'gym' : row[0], 'link' : link, 'region' : row[1], 'number' : row[2], 'description' : desc } )
            if ("%s%s"%(row[1],row[2])) not in regions.keys():
                regions[("%s%s"%(row[1],row[2]))] = [ { 'gym' : row[0], 'link' : link, 'region' : row[1], 'number' : row[2], 'description' : desc } ]
            else:
                regions[("%s%s"%(row[1],row[2]))].append( { 'gym' : row[0], 'link' : link, 'region' : row[1], 'number' : row[2], 'description' : desc } )
    
    rangeName = "'Links'!L2:M"
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheetId, range=rangeName).execute()
    values = result.get('values', [])
    if not values:
        print("Error: no users found.")
        return
    else:
        for row in values:
            descriptions[row[0]] = row[1]


def main():
    global commands, client
    commands = {';startlinking' : start_linking,
                 ';stoplinking' : stop_linking,
                 ';status' : status_check,
                 ';help' : print_help,
                 ';gym' : find_gym,
                 ';sector' : find_sector,
                 ';;;region;;;' : toggle_region_display,
                 ';;;init;;;' : initialize_channel }
    
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    discoveryUrl = ('https://sheets.googleapis.com/$discovery/rest?'
                    'version=v4')
    global service
    service = discovery.build('sheets', 'v4', http=http,
                              discoveryServiceUrl=discoveryUrl)
    update_lists()
            
    client.run('MzA1MjE0NTAyNzE3MzU4MDkx.DEH9Ew.RoHYn4kRyPKKb77ZqwjZOkd4_xQ')
    
    #gather_update()
    print("okay done now")
    
if __name__ == '__main__':
    main()
