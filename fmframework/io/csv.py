import csv
import datetime

headers = ['track', 'album', 'artist', 'time', 'track id', 'album id', 'artist id']

def exportScrobbles(scrobbles):

    date = str(datetime.datetime.now())

    with open('scrobbles.csv', 'w') as fileobj:

        writer = csv.DictWriter(fileobj, fieldnames = headers)
        writer.writeheader()

        for track in scrobbles:

            trackdict = {
                    'track':track['name'],
                    'album':track['album']['#text'],
                    'artist':track['artist']['#text'],
                    'time': datetime.datetime.fromtimestamp(int(track['date']['uts'])),
                    'track id':track['mbid'],
                    'album id':track['album']['mbid'],
                    'artist id':track['artist']['mbid']}

            writer.writerow(trackdict)
