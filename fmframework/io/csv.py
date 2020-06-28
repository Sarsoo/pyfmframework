from csv import DictWriter
import datetime
import logging
from typing import List
from fmframework.model import Scrobble

logger = logging.getLogger(__name__)
headers = ['track', 'album', 'artist', 'time', 'track id', 'album id', 'artist id']


def export_scrobbles(scrobbles: List[Scrobble], path: str):
    logger.info(f'dumping {len(scrobbles)} to {path}')
    date = str(datetime.date.today())

    with open('{}/{}_scrobbles.csv'.format(path, date), 'w') as fileobj:

        writer = DictWriter(fileobj, fieldnames=headers)
        writer.writeheader()

        for scrobble in scrobbles:
            writer.writerow({
                'track': scrobble.track.name.replace(';', '_').replace(',', '_'),
                'album': scrobble.track.album.name.replace(';', '_').replace(',', '_'),
                'artist': scrobble.track.artist.name.replace(';', '_').replace(',', '_'),
                'time': scrobble.time,
                'track id': scrobble.track.mbid,
                'album id': scrobble.track.album.mbid,
                'artist id': scrobble.track.artist.mbid
            })
