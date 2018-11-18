"""
Copyright (C) 2018  Allison Chilton

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""

from bs4 import BeautifulSoup
import spotipy
import spotipy.util as util
import requests
import pdb
from datetime import datetime
from datetime import timedelta
from dateutil import parser as dateparser
import copy
import json
import csv
import openpyxl
def dumpCsvToExcel():

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Cheap'
    with open(cheapcsv,'r') as f:
        for row in f:
            ws.append(row.split(',')[:-2])

    ws = wb.create_sheet('Expensive')
    with open(expcsv,'r') as f:
        for row in f:
            ws.append(row.split(',')[:-2])

    datefilter = openpyxl.worksheet.filters.CustomFilter('greaterThanOrEqual',datetime.now().strftime('%m-%d-%Y'))

    wb.save('concerts.xlsx')


def getShowsFromLink(link):
    shows = []
    re = requests.get(link)
    soup= BeautifulSoup(re.text,'lxml')
    results = soup.find_all('li', attrs={'class':'list-result'})
    for r in results:
        if 'inline-ad' in r.attrs['class']:
            continue
        artistname = r.find('a').text.strip()
        price = r.find('div',attrs={'class':'price'}).text.strip()
        datestr = r.find('div',attrs={'class':'time'}).text.strip()
        try:
            date = dateparser.parse(datestr)
            if date < datetime.now():
                date = date.replace(year=(date.year+1))
        except Exception:
            date = shows[-1:][0]['date']
            print("Couldn't find date for {}, setting it to last good date (could be wrong)".format(artistname))
        location = r.find('div',attrs={'class':'location'}).text.strip()
        entry = {'artist':artistname,'price':price,'date':date,'venue':location}
        shows.append(entry)
    return shows
    
def getShows():
    with open('links.json') as f:
        ld = json.load(f)
        cheaplinks = ld['cheap']
        explinks = ld['expensive']

    global cheapshows
    global expensiveshows
    cheapshows = []
    expensiveshows = []


    for link in cheaplinks:
        cheapshows.extend(getShowsFromLink(link))

    for link in explinks:
        expensiveshows.extend(getShowsFromLink(link))


    cheapshows = sorted(cheapshows,key=lambda x: x['date'])
    expensiveshows = sorted(expensiveshows,key=lambda x: x['date'])


def addShowsToPlaylist(shows,playlist_id):
    text = ""
    counter = 0
    for show in shows:
        artistname = show['artist']
        search = sp.search(q=artistname,type='artist',limit='5')

        for item in search['artists']['items']:
            if artistname.lower() == item['name'].lower():
                top_songs = sp.artist_top_tracks(item['uri'])['tracks']
                if len(top_songs) >= 2:
                    addsongs = [top_songs[0]['id'],top_songs[1]['id']]
                    sp.user_playlist_add_tracks(creds['username'],playlist_id,addsongs)
                    entry = copy.deepcopy(show)
                    entry['date'] = entry['date'].strftime('%m-%d-%Y')
                    entry['songs'] = ','.join(addsongs)
                    entry['deleted'] = False
                    e = list(entry.values())
                    e = [str(x) for x in e]
                    text += "{}\n".format(','.join(e))
                    counter += 1
                    break
                
        else:
            print("No tracks added for {}".format(artistname))

    #dont add header for empty runs
    if counter == 0:
        text = ''
        
    print("Added {} to {}".format(counter,playlist_id))
    return text

def deletePassed(showlist,playlist_id):
    delsongs = []
    for row in showlist:
        date = dateparser.parse(row['date'])
        now = datetime.now()
        if date < now:
            if abs(date-now) > timedelta(days=1):
                delsongs.extend([row['songid1'],row['songid2']])
                print('Deleting {}'.format(row['artist']))
                row['deleted'] = True
                #showlist.remove(row)

    import pdb
    pdb.set_trace()
    delsonglistlist = [delsongs[x*90:(x*90)+90] for x in range(int(len(delsongs)/90)+1)]

    
    for ds in delsonglistlist:
        sp.user_playlist_remove_all_occurrences_of_tracks(creds['username'],playlist_id,ds)


def isDupe(row,otherlist):
    for row2 in otherlist:
        if row['artist'] == row2['artist'] and row['date'].strftime('%m-%d-%Y') == row2['date'] and row['venue'] == row2['venue']:
            return True
    return False
    

            
def removeDupes():
    global cheapshows
    global expensiveshows
    
    cheapshows = [x for x in cheapshows if not isDupe(x,oldcheap)]
    expensiveshows = [x for x in expensiveshows if not isDupe(x,oldexp)]

def getOldText(showlist):
    text = 'artist,price,date,venue,songid1,songid2,deleted\n'
    for show in showlist:
        e = list(show.values())
        e = [str(x) for x in e]
        text += "{}\n".format(','.join(e))

    return text

        
        
        

scope = 'user-library-read,playlist-modify-private,playlist-modify-public'

with open('creds.json', 'r') as f:
    creds = json.load(f)
    

token = util.prompt_for_user_token(creds['username'],scope,client_id=creds['clientid'],client_secret=creds['secret'],redirect_uri='http://www.google.com')
sp = spotipy.Spotify(auth=token)

expplay = creds['expensive_playlist_id']
cheapplay = creds['cheap_playlist_id']

cheapcsv = 'cheap.csv'
expcsv = 'exp.csv'

with open(cheapcsv,'r') as f:
    reader = csv.DictReader(f)
    oldcheap = []
    for row in reader:
        if row['deleted'].lower() == 'false':
            oldcheap.append(row)

with open(expcsv,'r') as f:
    reader = csv.DictReader(f)
    oldexp = []
    for row in reader:
        if row['deleted'].lower() =='false':
            oldexp.append(row)

deletePassed(oldcheap,cheapplay)
deletePassed(oldexp,expplay)

getShows()
removeDupes()

oldtextcheap = getOldText(oldcheap)
oldtextexp = getOldText(oldexp)


cheapcsvtext = addShowsToPlaylist(cheapshows,cheapplay)
expcsvtext = addShowsToPlaylist(expensiveshows,expplay)
with open(cheapcsv,'w') as f:
    f.write(oldtextcheap)
    f.write(cheapcsvtext)


with open(expcsv,'w') as f:
    f.write(oldtextexp)
    f.write(expcsvtext)


dumpCsvToExcel()
