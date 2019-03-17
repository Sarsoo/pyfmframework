import csv
import datetime

headers = ['track', 'album', 'artist', 'time', 'track id', 'album id', 'artist id']

def exportScrobbles(scrobbles, path):

    date = str(datetime.datetime.now()).split(' ')[0]

    with open('{}/{}_scrobbles.csv'.format(path, date), 'w') as fileobj:

        writer = csv.DictWriter(fileobj, fieldnames = headers)
        writer.writeheader()

        for track in scrobbles:

            trackdict = {
                    'track':track['name'].replace(';', '_').replace(',', '_'),
                    'album':track['album']['#text'].replace(';', '_').replace(',', '_'),
                    'artist':track['artist']['#text'].replace(';', '_').replace(',', '_'),
                    'time': datetime.datetime.fromtimestamp(int(track['date']['uts'])),
                    'track id':track['mbid'],
                    'album id':track['album']['mbid'],
                    'artist id':track['artist']['mbid']}

            writer.writerow(trackdict)
